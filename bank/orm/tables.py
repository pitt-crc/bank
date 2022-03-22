"""Object-oriented definitions for the underlying database schema

API Reference
-------------
"""

from __future__ import annotations

from datetime import date
from logging import getLogger

from sqlalchemy import Column, Date, Integer, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates, relationship

from .utils import Validators, ProposalEnum
from .. import settings

LOG = getLogger('bank.orm.tables')
Base = declarative_base()
metadata = Base.metadata


class Proposal(Base, Validators):
    """Meta data for user proposals

    Table Fields:
      - id: Integer
      - account_name: String
      - proposal_type: ProposalEnum
      - start_date: Date
      - end_date: Date
      - percent_notified: Integer
    """

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    proposal_type = Column(Enum(ProposalEnum), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    percent_notified = Column(Integer, nullable=False)
    allocations = relationship('Allocation', backref='Allocation.proposal_id')

    @validates('percent_notified')
    def _validate_percent_notified(self, key: str, value: int) -> None:
        super()._validate_percent_notified(key, value)

    @property
    def expired(self) -> bool:
        """Return whether the investment is past its end date"""

        return self.end_date <= date.today()

    def allocated(self, cluster: str) -> int:
        """Return the service units allocated under the proposal for a given cluster

        Args:
            cluster: The name of the cluster
        """

        raise NotImplementedError

    def total_allocated(self) -> int:
        """Return the total service units allocated under the proposal"""

        return sum(getattr(self, c) for c in settings.clusters)


class Allocation(Base, Validators):
    """Service unit allocations on individual clusters

    Table Fields:
      - id: Integer
      - proposal_id: Integer
      - cluster_name: String
      - service_units: Integer
      - final_usage: Integer
      """

    __tablename__ = 'allocation'

    id = Column(Integer, primary_key=True)
    proposal_id = Column(Integer, ForeignKey(Proposal.id), primary_key=True)
    cluster_name = Column(String, nullable=False)
    service_units = Column(Integer, nullable=False)
    final_usage = Column(Integer, nullable=True)

    @validates('service_units')
    def _validate_service_units(self, key: str, value: int) -> None:
        super()._validate_service_units(key, value)


class Investor(Base, Validators):
    """Service unit allocations granted in exchange for user investment

    Table Fields:
      - id: Integer
      - account_name: String
      - start_date: Date
      - end_date: Date
      - service_units: Integer
      - current_sus: Integer
      - withdrawn_sus: Integer
      - rollover_sus: Integer
    """

    __tablename__ = 'investor'

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    service_units = Column(Integer, nullable=False)
    current_sus = Column(Integer, nullable=False)
    withdrawn_sus = Column(Integer, nullable=False)
    rollover_sus = Column(Integer, nullable=False)
    exhaustion_date = Column(Date, nullable=True)

    @validates('service_units')
    def _validate_service_units(self, key: str, value: int) -> None:
        super()._validate_service_units(key, value)

    @property
    def expired(self) -> bool:
        """Return whether the investment is past its end date or is fully withdrawn with no remaining service units"""

        return (self.end_date <= date.today()) or (self.current_sus == 0 and self.withdrawn_sus >= self.service_units)
