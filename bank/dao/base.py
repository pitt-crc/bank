from __future__ import annotations

from datetime import date
from typing import Optional, List

from sqlalchemy import select, or_, between

from bank.exceptions import MissingProposalError, MissingInvestmentError, BankAccountNotFoundError
from bank.orm import Session, Account, Proposal, Investment


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
            raise MissingProposalError(f'Account `{self._account_name}` does not have an associated proposal.')

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
            raise MissingProposalError(f'Account `{self._account_name}` does not have an associated proposal.')

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
            raise MissingInvestmentError(f'Account {self._account_name} has no associated investments')

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