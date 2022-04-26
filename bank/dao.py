from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import Optional, Union

import pandas as pd
from sqlalchemy import delete, select, or_, between

from bank import settings
from bank.exceptions import *
from bank.orm import ProposalEnum, Session, Account, Proposal, Investment, Allocation

LOG = getLogger('bank.dao.account_data')


# Todo: Revisit pandas functions during unit testing
class ProposalData:
    """Data access for proposals tied to a given account"""

    def __init__(self, account_name: str) -> None:
        """Retrieve proposal data for an existing bank account

        Args:
            account_name: The name of the account
        """

        self._account_name = account_name

    @staticmethod
    def _verify_cluster_values(**kwargs: int) -> None:
        """Raise a ``ValueError`` if given cluster names or service units are invalid"""

        for cluster, sus in kwargs.items():
            if cluster not in settings.clusters:
                raise ValueError(f'{cluster} is not a valid cluster name.')

            if sus < 0:
                raise ValueError('Service units cannot be negative.')

    def _verify_proposal_id(self, pid: int) -> None:
        """Raise a ``MissingProposalError`` if a given ID does not belong to the current account"""

        if not self.check_id_matches_account(pid):
            raise MissingProposalError(f'Account `{self._account_name}` has no proposal with {pid}.')

    def check_id_matches_account(self, pid: int) -> bool:
        """Return whether a given proposal ID belongs to the current account

        Args:
            pid: The ID to compare against the current account

        Returns:
            Boolean representing whether ID matches the current account
        """

        query = select(Proposal).join(Account).where(Account.name == self._account_name).where(Proposal.id == pid)
        with Session() as session:
            return session.execute(query).scalars().first() is not None

    def get_current_proposal_data(self, active_only: bool = True) -> pd.DataFrame:
        """Return a tabular summary of current account proposals

        Args:
            active_only: Only return a summary of active proposals

        Returns:
            A ``DataFrame`` with proposal information
        """

        query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(Proposal.start_date <= date.today()) \
            .where(Proposal.end_date > date.today())

        if active_only:
            query = query.where(Proposal.is_active)

        with Session() as session:
            return pd.read_sql_query(query, session.connection())

    def get_proposal_data_in_range(self, start: date, end: date, active_only: bool = True) -> pd.DataFrame:
        """Return a tabular summary of account proposals overlying a given date range

        Args:
            start: Start date to search for proposals in
            end: End date to search for proposals in
            active_only: Only return a summary of active proposals

        Returns:
            A ``DataFrame`` with proposal information
        """

        query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(
            or_(
                between(start, Proposal.start_date, Proposal.end_date),
                between(end, Proposal.start_date, Proposal.end_date),
                between(Proposal.start_date, start, end),
                between(Proposal.end_date, start, end)
            )
        )

        if active_only:
            query = query.where(Proposal.is_active)

        with Session() as session:
            return pd.read_sql_query(query, session.connection())

    def create_proposal(
            self,
            type: ProposalEnum = ProposalEnum.Proposal,
            start: date = date.today(),
            duration: int = 365,
            **kwargs: int
    ) -> None:
        """Create a new proposal for the account

        Args:
            type: The type of the proposal
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to allocate to each cluster
        """

        with Session() as session:
            # Create the new proposal and allocations
            new_proposal = Proposal(
                proposal_type=type,
                percent_notified=0,
                start_date=start,
                end_date=start + timedelta(days=duration),
                allocations=[
                    Allocation(cluster_name=cluster, service_units=sus) for cluster, sus in kwargs.items()
                ]
            )

            # Assign the proposal to user account
            account_query = select(Account).where(Account.name == self._account_name)
            account = session.execute(account_query).scalars().first()
            account.proposals.append(new_proposal)

            session.add(account)
            session.commit()
            LOG.info(f"Created proposal {new_proposal.id} for {self._account_name}")

    def delete_proposal(self, pid: int = None) -> None:
        """Delete a proposal from the current account

        Args:
            pid: ID of the proposal to delete
        """

        self._verify_proposal_id(pid)
        with Session() as session:
            session.execute(delete(Proposal).where(Proposal.id == pid))
            session.execute(delete(Allocation).where(Allocation.proposal_id == pid))
            session.commit()
            LOG.info(f"Deleted proposal {pid} for {self._account_name}")

    def modify_proposal(
            self,
            pid: int,
            type: ProposalEnum = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            **kwargs: Union[int, date]
    ) -> None:
        """Overwrite the properties of a given proposal

        Args:
            pid: The ID of the proposal to modify
            type: Optionally change the type of the proposal
            start_date: Optionally set a new start date for the proposal
            end_date: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the given ID does not match the current account
            ValueError: For invalid cluster names of service units
        """

        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        query = select(Proposal).where(Proposal.id == pid)
        with Session() as session:
            proposal = session.execute(query).scalars().first()
            proposal.proposal_type = type or proposal.proposal_type
            proposal.start_date = start_date or proposal.start_date
            proposal.end_date = end_date or proposal.end_date

            for allocation in proposal.allocations:
                allocation.service_units = kwargs.get(allocation.cluster_name, allocation.service_units)

            session.commit()
            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Overwrote {kwargs}")

    def add_sus(self, pid: int, **kwargs: int) -> None:
        """Add service units to a given proposal

        Args:
            pid: The ID of the proposal to modify
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the given ID does not match the current account
            ValueError: For invalid cluster names of service units
        """

        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        query = select(Allocation).join(Proposal).where(Proposal.id == pid)
        with Session() as session:
            allocations = session.execute(query).scalars().all()
            for allocation in allocations:
                allocation.service_units += kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {pid} for account {self._account_name}. Added {kwargs}")

    def subtract_sus(self, pid: int, **kwargs: int) -> None:
        """Subtract service units to a given proposal

        Args:
            pid: The ID of the proposal to modify
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the given ID does not match the current account
            ValueError: For invalid cluster names of service units
        """

        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        query = select(Allocation).join(Proposal).where(Proposal.id == pid)
        with Session() as session:
            allocations = session.execute(query).scalars().all()
            for allocation in allocations:
                allocation.service_units -= kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {pid} for account {self._account_name}. Removed {kwargs}")


class InvestmentData:
    """Data access for a single account's investment information"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account
        """

        super().__init__(account_name)

    def _verify_service_units(self, sus):

        if sus <= 0:
            raise ValueError('Service units must be greater than zero.')

    def create_investment(self, sus: int, start: date = date.today(), duration: int = 365, num_inv: int = 1) -> None:
        """Add a new investment(s) for the given account

        ``num_inv`` reflects the number of investments to create. If the argument
        is greater than one, repeating investments are created sequentially such
        that a new investment begins as each investment ends. The ``start``
        argument represents the start date of the first investment in the sequence.
        The given number of service units (``sus``) are allocated equally across
        each investment in the series.

        Args:
            sus: The number of service units to add
            start: The start date of the proposal
            duration: How many days before the investment expires
            num_inv: Spread out the given service units equally across given number of instances
        """

        if num_inv < 1:
            raise ValueError('Argument ``repeat`` must be >= 1')

        # Calculate number of service units per each investment
        duration = timedelta(days=duration)
        sus_per_instance = ceil(sus / num_inv)

        with Session() as session:
            self.get_proposal(session)

            for i in range(num_inv):
                start_this = start + i * duration
                end_this = start + (i + 1) * duration

                new_investment = Investment(
                    start_date=start_this,
                    end_date=end_this,
                    service_units=sus_per_instance,
                    current_sus=sus_per_instance,
                    withdrawn_sus=0,
                    rollover_sus=0
                )

                account = self.get_account(session)
                account.investments.append(new_investment)
                session.add(account)
                LOG.debug(f"Inserting investment {new_investment.id} for {self._account_name} with allocation of `{sus}`")

                session.commit()

            LOG.info(f"Invested {sus} service units for account {self._account_name}")

    def delete_investment(self, id: int) -> None:
        """Delete one of the account's associated investments

        Args:
            id: The id of the investment to delete
        """

        with Session() as session:
            investment = self.get_investment(session, id)
            session.query(Investment).filter(Investment.id == investment.id).delete()

            session.commit()
            LOG.info(f'Archived investment {investment.id} for account {self._account_name}')

    def add_sus(self, id: int, sus: int) -> None:
        """Add service units to the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to add

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._verify_service_units(sus)
        with Session() as session:
            investment = self.get_investment(session, id)
            investment.service_units += sus
            investment.current_sus += sus

            session.commit()
            LOG.info(f'Added {sus} service units to investment {investment.id} for account {self._account_name}')

    def subtract(self, id: int, sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to remove

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._verify_service_units(sus)
        with Session() as session:
            investment = self.get_investment(session, id)
            if investment.current_sus < sus:
                raise ValueError(f'Cannot subtract {sus}. Investment {id} only has {investment.current_sus} available.')

            investment.service_units -= sus
            investment.current_sus -= sus

            session.commit()
            LOG.info(f'Removed {sus} service units to investment {investment.id} for account {self._account_name}')

    def overwrite(self, id: int, sus: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> None:
        """Overwrite service units allocated to the given investment

        Args:
            id: The id of the investment to change
            sus: New number of service units to assign to the investment
            start_date: Optionally set a new start date for the investment
            end_date: Optionally set a new end date for the investment

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        with Session() as session:
            investment = self.get_investment(session, id)

            if sus is not None:
                self._verify_service_units(sus)
                investment.service_units = sus

            if start_date:
                investment.start_date = start_date

            if end_date:
                investment.end_date = end_date

            session.commit()
            LOG.info(f'Overwrote service units on investment {investment.id} to {sus} for account {self._account_name}')
