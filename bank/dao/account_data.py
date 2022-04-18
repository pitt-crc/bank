from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import Optional, Union

from sqlalchemy import delete

from bank import settings
from bank.dao.base import AccountQueryBase
from bank.exceptions import *
from bank.orm import Investment, Session
from bank.orm import ProposalEnum, Proposal, Allocation

LOG = getLogger('bank.dao.account_data')


class ProposalData(AccountQueryBase):
    """Data access for a single account's proposal information"""

    def _verify_cluster_values(self, **kwargs):
        for cluster, sus in kwargs.items():
            if cluster not in settings.clusters:
                raise ValueError(f'{cluster} is not a valid cluster name.')

            if sus < 0:
                raise ValueError('Service units cannot be negative.')

    def create_proposal(
            self,
            type: ProposalEnum = ProposalEnum.Proposal,
            start: date = date.today(),
            duration: int = 365,
            **kwargs: int
    ) -> None:
        """Create a new proposal for the given account

        Args:
            type: The type of the proposal
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to add on to each cluster
        """

        with Session() as session:
            # Check for any overlapping proposals
            end_date = start + timedelta(days=duration)
            if self.get_overlapping_proposals(session, start, end_date):
                raise ProposalExistsError(f'Proposal already exists for account: {self._account_name}')

            # Create the new proposal and allocations
            new_proposal = Proposal(
                proposal_type=type,
                percent_notified=0,
                start_date=start,
                end_date=end_date,
                allocations=[
                    Allocation(cluster_name=cluster, service_units=sus) for cluster, sus in kwargs.items()
                ]
            )

            # Assign the proposal to user account
            account = self.get_account(session)
            account.proposals.append(new_proposal)

            session.add(account)
            session.commit()
            LOG.info(f"Created proposal {new_proposal.id} for {self._account_name}")

    def delete_proposal(self, pid: Optional[int] = None) -> None:
        """Delete the account's current proposal"""

        with Session() as session:
            proposal = self.get_proposal(session, pid=pid)
            session.execute(delete(Proposal).where(Proposal.id == proposal.id))
            session.execute(delete(Allocation).where(Allocation.proposal_id == proposal.id))
            session.commit()
            LOG.info(f"Deleted proposal {proposal.id} for {self._account_name}")

    def modify_proposal(
            self,
            pid: Optional[int] = None,
            type: ProposalEnum = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            **kwargs: Union[int, date]
    ) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            type: Optionally change the type of the proposal
            start_date: Optionally set a new start date for the proposal
            end_date: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        self._verify_cluster_values(**kwargs)
        with Session() as session:
            proposal = self.get_proposal(session, pid=pid)
            proposal.proposal_type = type or proposal.proposal_type
            proposal.start_date = start_date or proposal.start_date
            proposal.end_date = end_date or proposal.end_date

            for allocation in proposal.allocations:
                allocation.service_units = kwargs.get(allocation.cluster_name, allocation.service_units)

            session.commit()
            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Overwrote {kwargs}")

    def add_sus(self, pid: Optional[int] = None, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        self._verify_cluster_values(**kwargs)
        with Session() as session:
            proposal = self.get_proposal(session, pid=pid)
            for allocation in proposal.allocations:
                allocation.service_units += kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Added {kwargs}")

    def subtract_sus(self, pid: Optional[int] = None, **kwargs: int) -> None:
        """Subtract service units from the account's current allocation

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        self._verify_cluster_values(**kwargs)
        with Session() as session:
            proposal = self.get_proposal(session, pid=pid)
            for allocation in proposal.allocations:
                allocation.service_units -= kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Removed {kwargs}")


class InvestmentData(AccountQueryBase):
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
