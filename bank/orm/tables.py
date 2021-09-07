"""Object oriented interface for tables in the application database.

API Reference
-------------
"""

from sqlalchemy import Column, Date, Enum, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from .mixins import CustomBase
from ..settings import app_settings
from ..utils import ProposalType

Base = declarative_base(cls=CustomBase)
metadata = Base.metadata


class Investor(Base):
    """Class representation of the ``investor`` table"""

    __tablename__ = 'investor'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    proposal_type = Column(Integer)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    withdrawn_sus = Column(Integer)
    rollover_sus = Column(Integer)


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


class Proposal(Base, CustomBase):
    """Class representation of the ``proposal`` table"""

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    _percent_notified = Column('percent_notified', Integer)
    proposal_type = Column(Enum(ProposalType))

    @property
    def percent_notified(self) -> int:
        return self._percent_notified

    @percent_notified.setter
    def percent_notified(self, val: int) -> None:
        if (val < 0) or (100 < val):
            raise ValueError('percent_notified value must be between 0 and 100')

        self._percent_notified = val


class ProposalArchive(Base, CustomBase):
    """Class representation of the ``proposal_archive`` table"""

    __tablename__ = 'proposal_archive'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)


# Dynamically add columns for each of the managed clusters
for cluster in app_settings.clusters:
    setattr(Proposal, cluster, Column(Integer))
    setattr(ProposalArchive, cluster, Column(Integer))
    setattr(ProposalArchive, cluster + '_usage', Column(Integer))
