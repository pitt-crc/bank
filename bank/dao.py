from __future__ import annotations

from typing import List, Union, Optional

from sqlalchemy import select, between, or_

from .exceptions import *
from .orm import Investor, Proposal, Session
from .system import SlurmAccount


class DataAccessObject:
    """Base class for building data access objects"""

    def __init__(self, account_name: str) -> None:
        """Manage an existing proposal in the bank

        Args:
            account_name: The name of the account
        """

        self.account_name = account_name
        self._slurm_acct = SlurmAccount(account_name)

    def get_proposal(self, session: Session, pid: Optional[int] = None) -> Proposal:
        """Return the proposal record from the application database

        Args:
            session: An open database session to use for executing queries

        Returns:
            An entry in the Proposal database

        Raises:
            MissingProposalError: If the account has no associated proposal
        """

        query = select(Proposal).where(Proposal.account_name == self.account_name)
        if pid:
            query = query.where(Proposal.id == pid)

        else:
            query = query.where(Proposal.is_active == True)

        proposal = session.execute(query).scalars().first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

        return proposal

    def get_overlapping_proposals(self, session, start, end_date):
        query = select(Proposal).where(
            or_(
                between(start, Proposal.start_date, Proposal.end_date),
                between(end_date, Proposal.start_date, Proposal.end_date),
                between(Proposal.start_date, start, end_date),
                between(Proposal.end_date, start, end_date)
            )
        )
        existing_proposal = session.execute(query).scalars().all()
        return existing_proposal

    def _get_investment(self, session: Session, id: Optional[int] = None) -> Union[Investor, List[Investor]]:
        """Return any investments associated with the account from the application database

        Args:
            session: An open database session to use for executing queries
            id: Optionally return a single investment with the given id instead of all investments

        Returns:
            One or more entries in the Investment Database
        """

        if id:
            inv = session.query(Investor).filter(Investor.account_name == self.account_name, Investor.id == id).first()
            error = f'Account {self.account_name} has no investment with id {id}'

        else:
            inv = session.query(Investor).filter(Investor.account_name == self.account_name).order_by(Investor.start_date).all()
            error = f'Account {self.account_name} has no associated investments'

        if not inv:
            raise MissingInvestmentError(error)

        return inv
