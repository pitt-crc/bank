from __future__ import annotations

from typing import List, Union, Optional

from sqlalchemy import select, between, or_

from .exceptions import *
from .orm import Investment, Proposal, Session


class DataAccessObject:
    """Encapsulates SQL queries for common data retrieval tasks"""

    def __init__(self, account_name: str) -> None:
        """Retrieve data for an existing bank account

        Args:
            account_name: The name of the account
        """

        self.account_name = account_name

    def get_proposal(self, session: Session, pid: Optional[int] = None) -> Proposal:
        if pid is None:
            return self.get_primary_proposal(session)

        return self.get_proposal_by_id(session, pid)

    def get_primary_proposal(self, session: Session) -> Proposal:
        """Return the account's currently active proposal

        Args:
            session: An open database session to use for executing queries

        Returns:
            An entry in the Proposal database

        Raises:
            MissingProposalError: If the account has currently active proposal
        """

        query = select(Proposal).where(Proposal.account_name == self.account_name).where(Proposal.is_active == True)
        proposal = session.execute(query).scalars().first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

        return proposal

    def get_proposal_by_id(self, session: Session, pid: int) -> Proposal:
        """Return the account's currently active proposal

        Args:
            session: An open database session to use for executing queries
            pid: The ID of the proposal to return

        Returns:
            An entry in the Proposal database

        Raises:
            MissingProposalError: If the account has no associated proposal with the given ID
        """

        query = select(Proposal).where(Proposal.account_name == self.account_name).where(Proposal.id == pid)
        proposal = session.execute(query).scalars().first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

        return proposal

    def get_overlapping_proposals(self, session, start, end_date):
        """Return any proposals that overlap the given date range

        Args:
            session: An open database session to use for executing queries
            start: Starting date to search after
            end_date: Ending date to search before

        Returns:

        """

        query = select(Proposal) \
            .where(Proposal.account_name == self.account_name) \
            .where(
            or_(
                between(start, Proposal.start_date, Proposal.end_date),
                between(end_date, Proposal.start_date, Proposal.end_date),
                between(Proposal.start_date, start, end_date),
                between(Proposal.end_date, start, end_date)
            )
        )

        return session.execute(query).scalars().all()

    def get_all_proposals(self, session: Session):
        query = select(Proposal).where(Proposal.account_name == self.account_name)
        return session.execute(query).scalars().all()

    def get_investment(self, session: Session, inv_id: Optional[int]):
        raise NotImplementedError()

    def get_primary_investment(self, session: Session) -> Union[Investment, List[Investment]]:
        """Return any investments associated with the account from the application database

        Args:
            session: An open database session to use for executing queries
            id: Optionally return a single investment with the given id instead of all investments

        Returns:
            One or more entries in the Investment Database
        """

        inv = session.query(Investment).filter(Investment.account_name == self.account_name).order_by(Investment.start_date).all()
        if not inv:
            raise MissingInvestmentError(f'Account {self.account_name} has no associated investments')

        return inv

    def get_investment_by_id(self, session: Session, inv_id: int) -> Investment:
        """Return any investments associated with the account from the application database

        Args:
            session: An open database session to use for executing queries
            id: Optionally return a single investment with the given id instead of all investments

        Returns:
            One or more entries in the Investment Database
        """

        inv = session.query(Investment).filter(Investment.account_name == self.account_name, Investment.id == inv_id).first()
        if inv is None:
            raise MissingInvestmentError(f'Account {self.account_name} has no investment with id {inv_id}')

        return inv

    def get_all_investments(self, session: Session):
        query = select(Investment).where(Investment.account_name == self.account_name)
        return session.execute(query).scalars().all()
