from sqlalchemy import Column, Date, Enum, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from .mixins import CustomBase
from ..settings import app_settings
from ..utils import PercentNotified, ProposalType

Base = declarative_base(cls=CustomBase)
metadata = Base.metadata


class Investor(Base):
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
    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    percent_notified = Column(Enum(PercentNotified))
    proposal_type = Column(Enum(ProposalType))


class ProposalArchive(Base, CustomBase):
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
