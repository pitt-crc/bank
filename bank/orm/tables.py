"""Object oriented definitions for the underlying database schema

API Reference
-------------
"""

from __future__ import annotations

from datetime import date
from itertools import chain
from logging import getLogger

from sqlalchemy import Column, Date, Enum, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates

from .base import CustomBase
from .enum import ProposalType
from ..settings import app_settings
from ..system import SlurmAccount

Base = declarative_base(cls=CustomBase)
metadata = Base.metadata

LOG = getLogger('bank.orm')


class Proposal(Base):
    """Class representation of the ``proposal`` table"""

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    percent_notified = Column(Integer, nullable=False)
    proposal_type = Column(Enum(ProposalType), nullable=False)

    @validates('percent_notified')
    def validate_percent_notified(self, key: str, value: int) -> int:
        """Verify the given value is between 0 and 100"""

        if 0 <= value <= 100:
            return value

        raise ValueError('percent_notified value must be between 0 and 100')

    @validates(*app_settings.clusters)
    def validate_service_units(self, key: str, value: int) -> int:
        """Verify the given value is a non-negative integer"""

        if value < 0:
            raise ValueError(f'Invalid value for column {key} - Service units must be a non-negative integer.')

        return value

    def to_archive_object(self) -> ProposalArchive:
        """Return data from the current row as an ``InvestorArchive`` instance"""

        archive_obj = ProposalArchive(
            id=self.id,
            account_name=self.account_name,
            start_date=self.start_date,
            end_date=self.end_date,
            proposal_type=self.proposal_type
        )

        for cluster in app_settings.clusters:
            setattr(archive_obj, cluster, getattr(self, cluster))

        try:
            slurm_acct = SlurmAccount(self.account_name)
            for cluster in app_settings.clusters:
                setattr(archive_obj, f'{cluster}_usage', slurm_acct.get_cluster_usage(cluster))

        # If slurm isn't installed, leave the usage columns empty
        except:
            pass

        return archive_obj


class ProposalArchive(Base):
    """Class representation of the ``proposal_archive`` table"""

    __tablename__ = 'proposal_archive'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    proposal_type = Column(Enum(ProposalType), nullable=False)

    @validates(*chain(app_settings.clusters, (f'{c}_usage' for c in app_settings.clusters)))
    def validate_service_units(self, key: str, value: int) -> int:
        """Verify the given value is a non-negative integer"""

        if value < 0:
            raise ValueError(f'Invalid value for column {key} - Service units must be a non-negative integer.')

        return value


class Investor(Base):
    """Class representation of the ``investor`` table"""

    __tablename__ = 'investor'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    service_units = Column(Integer, nullable=False)
    current_sus = Column(Integer, nullable=False)
    withdrawn_sus = Column(Integer, nullable=False)
    rollover_sus = Column(Integer, nullable=False)

    @property
    def expired(self) -> bool:
        """Return whether the investment is past its end date or is fully withdrawn with no remaining service units."""

        return (self.end_date <= date.today()) or (self.current_sus == 0 and self.withdrawn_sus == self.service_units)

    def to_archive_object(self) -> InvestorArchive:
        """Return data from the current row as an ``InvestorArchive`` instance"""

        return InvestorArchive(
            id=self.id,
            account_name=self.account_name,
            start_date=self.start_date,
            end_date=self.end_date,
            exhaustion_date=date.today(),
            service_units=self.service_units,
            current_sus=self.current_sus
        )


class InvestorArchive(Base):
    """Class representation of the ``investor_archive`` table"""

    __tablename__ = 'investor_archive'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    exhaustion_date = Column(Date, nullable=False)
    service_units = Column(Integer, nullable=False)
    current_sus = Column(Integer, nullable=False)


# Dynamically add columns for each of the managed clusters
for _cluster in app_settings.clusters:
    setattr(Proposal, _cluster, Column(Integer, nullable=False))
    setattr(ProposalArchive, _cluster, Column(Integer, nullable=False))
    setattr(ProposalArchive, f'{_cluster}_usage', Column(Integer))
