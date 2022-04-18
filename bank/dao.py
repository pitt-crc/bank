from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import Optional, List, Union

from sqlalchemy import delete, select, or_, between

from bank import settings
from bank.exceptions import *
from bank.orm import ProposalEnum, Session, Account, Proposal, Investment, Allocation

LOG = getLogger('bank.dao.account_data')


class AccountQueryBase:
    """Encapsulates common DB queries as methods for use by child classes"""

    def __init__(self, account_name: str) -> None:
        """Retrieve data for an existing bank account

        Args:
            account_name: The name of the account
        """

        self._account_name = account_name

    def get_account(self, session: Session) -> Account:
        """Return entry from ``account`` table corresponding to the current account

        Args:
            session: Database session to use when executing the query

        Returns:
            Entry from the ``account`` table as an ``Account`` instance
        """

        stmt = select(Account).where(Account.name == self._account_name)
        result = session.execute(stmt).scalars().first()
        if result is None:
            raise BankAccountNotFoundError(f'No account found for {self._account_name}')

        return result

    def get_proposal(self, session: Session, pid: Optional[int] = None) -> Optional[Proposal]:
        """Convenience function for combining the ``get_primary_proposal`` and ``get_proposal_by_id``

        Return the account's currently active proposal. Optionally, specify
        ``pid`` to return a specific proposal tied to the current account.

        Args:
            session: Database session to use when executing the query
            pid: Optional return the proposal with the given ID

        Raises:
            MissingProposalError: If ``pid`` is ``None`` and the account has no currently active proposal
        """

        if pid is None:
            return self.get_primary_proposal(session)

        return self.get_proposal_by_id(session, pid)

    def get_primary_proposal(self, session: Session) -> Proposal:
        """Return the account's currently active proposal

        Args:
            session: Database session to use when executing the query

        Raises:
            MissingProposalError: If the account doesn't have an active proposal
        """

        query = select(Proposal).join(Account).where(Account.name == self._account_name).where(Proposal.is_active == True)
        proposal = session.execute(query).scalars().first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self._account_name}` does not have an active proposal.')

        return proposal

    def get_proposal_by_id(self, session: Session, pid: int) -> Proposal:
        """Return a specific proposal tied to the current account.

        Args:
            session: Database session to use when executing the query
            pid: The ID of the proposal to return

        Raises:
            MissingProposalError: If the account has no associated proposal with the given ID
        """

        query = select(Proposal).join(Account).where(Account.name == self._account_name).where(Proposal.id == pid)
        proposal = session.execute(query).scalars().first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self._account_name}` has no proposal with {pid}.')

        return proposal

    def get_overlapping_proposals(self, session: Session, start: date, end_date: date) -> List[Proposal]:
        """Return any proposals tied to the current account that overlap the given date range

        Args:
            session: Database session to use when executing the query
            start: Starting date to search after
            end_date: Ending date to search before

        Returns:
            A list of ``Proposal`` instances from the ``proposal`` database
        """

        query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(
            or_(
                between(start, Proposal.start_date, Proposal.end_date),
                between(end_date, Proposal.start_date, Proposal.end_date),
                between(Proposal.start_date, start, end_date),
                between(Proposal.end_date, start, end_date)
            )
        )

        return session.execute(query).scalars().all()

    def get_allocation(self, session: Session, cluster: str, pid: Optional[int] = None) -> Allocation:
        proposal = self.get_proposal(session, pid=pid)
        query = select(Allocation) \
            .where(Allocation.proposal_id == proposal.id) \
            .where(Allocation.cluster_name == cluster)

        return session.execute(query).scalars().first()

    def get_all_proposals(self, session: Session) -> List[Proposal]:
        """Return all proposals tied to the current account

        Args:
            session: Database session to use when executing the query

        Returns:
            A list of ``Proposal`` instances from the ``proposal`` database
        """

        query = select(Proposal).join(Account).where(Account.name == self._account_name)
        return session.execute(query).scalars().all()

    def get_investment(self, session: Session, inv_id: Optional[int]) -> Investment:
        """Convenience function combining the ``get_primary_investment`` and ``get_investment_by_id``

        Return the account's currently active investment. Optionally, specify
        ``inv_id`` to return a specific investment tied to the current account.

        Args:
            session: Database session to use when executing the query
            inv_id: Optional return the investment with the given ID

        Raises:
            MissingInvestmentError: If ``inv_id`` is ``None`` and the account has no currently active investment
        """

        if inv_id is None:
            return self.get_primary_investment(session)

        return self.get_investment_by_id(session, inv_id)

    def get_primary_investment(self, session: Session) -> Investment:
        """Return the account's currently active investment

        Args:
            session: Database session to use when executing the query

        Raises:
            MissingInvestmentError: If the account doesn't have an active investment
        """

        query = select(Investment).join(Account).where(Account.name == self._account_name).where(Investment.is_active == True)
        inv = session.execute(query).scalars().first()
        if not inv:
            raise MissingInvestmentError(f'Account {self._account_name} has no active investment')

        return inv

    def get_investment_by_id(self, session: Session, inv_id: int) -> Investment:
        """Return a specific investment tied to the current account.

        Args:
            session: Database session to use when executing the query
            inv_id: The ID of the investment to return

        Raises:
            MissingInvestmentError: If the account has no associated investment with the given ID
        """

        query = select(Investment).join(Account).where(Account.name == self._account_name).where(Investment.id == inv_id)
        inv = session.execute(query).scalars().first()
        if inv is None:
            raise MissingInvestmentError(f'Account {self._account_name} has no investment with id {inv_id}')

        return inv

    def get_all_investments(self, session: Session) -> List[Investment]:
        """Return all investments tied to the current account

        Args:
            session: Database session to use when executing the query

        Returns:
            A list of ``Investment`` instances from the ``investment`` database
        """

        query = select(Investment).join(Account).where(Account.name == self._account_name)
        return session.execute(query).scalars().all()


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
