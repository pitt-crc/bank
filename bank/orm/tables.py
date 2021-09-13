"""Object oriented interface for tables in the application database.

API Reference
-------------
"""

from __future__ import annotations

from logging import getLogger

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from bank.utils import ShellCmd
from .mixins import CustomBase
from ..exceptions import MissingProposalError
from ..settings import app_settings
from ..utils import ProposalType

Base = declarative_base(cls=CustomBase)
metadata = Base.metadata

LOG = getLogger('bank.orm')


class Account(Base):
    """Class representation of the ``account`` table"""

    __tablename__ = 'account'
    id = Column(Integer, primary_key=True)
    account_name = Column(Text(length=60))
    proposal = relationship('Proposal', back_populates='account', uselist=False)
    investments = relationship('Investor', back_populates='account')

    def require_proposal(self) -> None:
        """Raise an error if the account does not have a proposal

        Raises:
            MissingProposalError
        """

        if self.proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

    @property
    def email(self) -> str:
        """The email associated with the given user account"""

        cmd = ShellCmd(f'sacctmgr show account {self.account_name} -P format=description -n')
        return f'{cmd.out}{app_settings.email_suffix}'

    @property
    def locked_state(self) -> bool:
        """Return whether the account is locked"""

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out


class Proposal(Base, CustomBase):
    """Class representation of the ``proposal`` table"""

    __tablename__ = 'proposal'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    _percent_notified = Column('percent_notified', Integer)
    proposal_type = Column(Enum(ProposalType))

    account = relationship('Account', back_populates='proposal')

    @property
    def percent_notified(self) -> int:
        return self._percent_notified

    @percent_notified.setter
    def percent_notified(self, val: int) -> None:
        if (val < 0) or (val > 100):
            raise ValueError('percent_notified value must be between 0 and 100')

        self._percent_notified = val


class ProposalArchive(Base, CustomBase):
    """Class representation of the ``proposal_archive`` table"""

    __tablename__ = 'proposal_archive'
    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)


class Investor(Base):
    """Class representation of the ``investor`` table"""

    __tablename__ = 'investor'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    proposal_type = Column(Integer)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    withdrawn_sus = Column(Integer)
    rollover_sus = Column(Integer)

    account = relationship('Account', back_populates='investments')


class InvestorArchive(Base):
    """Class representation of the ``investor_archive`` table"""

    __tablename__ = 'investor_archive'
    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    exhaustion_date = Column(Date)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    proposal_id = Column(Integer)
    investor_id = Column(Integer)


# Dynamically add columns for each of the managed clusters
for cluster in app_settings.clusters:
    setattr(Proposal, cluster, Column(Integer))
    setattr(ProposalArchive, cluster, Column(Integer))
    setattr(ProposalArchive, cluster + '_usage', Column(Integer))
