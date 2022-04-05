"""Object-oriented definitions for the underlying database schema

API Reference
-------------
"""

from __future__ import annotations

from datetime import date
from logging import getLogger

from sqlalchemy import Column, Date, Integer, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates, relationship

from utils import Validators, ProposalEnum

LOG = getLogger('bank.orm.tables')
Base = declarative_base()
metadata = Base.metadata


class Account(Base):
    """User account data

    Table Fields:
      - id  (Integer): Primary key for this table
      - name (String): Account name of the proposal holder

    Relationships:
      - proposals     (Proposal): One to many
      - investments (Investment): One to many
    """

    __tablename__ = 'account'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    proposals = relationship('Proposal', back_populates='account')
    investments = relationship('Investment', back_populates='account')


class Proposal(Base, Validators):
    """Metadata for user proposals

    Table Fields:
      - id                 (Integer): Primary key for this table
      - account_id         (Integer): Primary key for this table for the ``account`` table
      - proposal_type (ProposalEnum): The proposal type
      - start_date            (Date): The date when the proposal goes into effect
      - end_date              (Date): The proposal's expiration date
      - percent_notified   (Integer): Percent usage when account holder was last notified

    Relationships:
      - account        (Account): Many to one
      - allocations (Allocation): One to many
    """

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(Account.id))
    proposal_type = Column(Enum(ProposalEnum), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    percent_notified = Column(Integer, nullable=False, default=0)

    account = relationship('Account', back_populates='proposals')
    allocations = relationship('Allocation', back_populates='proposal')

    @validates('percent_notified')
    def _validate_percent_notified(self, key: str, value: int) -> None:
        super()._validate_percent_notified(key, value)

    @hybrid_property
    def is_expired(self) -> bool:
        """Return whether the proposal is past its end date or has exhausted its allocation"""

        has_allocations = any(self.allocations.final_usage is None)
        past_date = self.end_date <= date.today()
        return past_date or not has_allocations

    @hybrid_property
    def is_active(self) -> bool:
        """Return whether the proposal is currently being utilized by the account"""

        today = date.today()
        in_date_range = (self.start_date <= today) and (today < self.end_date)
        has_allocations = any(self.allocations.final_usage is None)
        return in_date_range and has_allocations


class Allocation(Base, Validators):
    """Service unit allocations on individual clusters

    Values for the ``final_usage`` may column exceed the ``service_units``
    column in situations where system administrators have bypassed the banking
    system and manually enabled continued usage of a cluster after an allocation
    has run out.

    Table Fields:
      - id             (Integer): Primary key for this table
      - proposal_id (ForeignKey): Primary key for the ``proposal`` table
      - cluster_name    (String): Name of the allocated cluster
      - service_units  (Integer): Number of allocated service units
      - final_usage    (Integer): Total service units utilized at proposal expiration

    Relationships:
      - proposal (Proposal): Many to one
    """

    __tablename__ = 'allocation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey(Proposal.id))
    cluster_name = Column(String, nullable=False)
    service_units = Column(Integer, nullable=False)
    final_usage = Column(Integer, nullable=True)

    proposal = relationship('Proposal', back_populates='allocations')

    @validates('service_units')
    def _validate_service_units(self, key: str, value: int) -> None:
        super()._validate_service_units(key, value)


class Investment(Base, Validators):
    """Service unit allocations granted in exchange for user investment

    Table Fields:
      - id            (Integer): Primary key for this table
      - start_date       (Date): Date the investment goes into effect
      - end_date         (Date): Expiration date of the investment
      - service_units (Integer): Total service units granted by an investment
      - rollover_sus  (Integer): Service units carried over from a previous investment
      - withdrawn_sus (Integer): Service units removed from this investment and into another
      - current_sus   (Integer): Total service units available in the investment
      - exhaustion_date  (Date): Date the investment is_expired or reached full utilization

    Relationships:
      - account (Account): Many to one
    """

    __tablename__ = 'investment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(Account.id))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    service_units = Column(Integer, nullable=False)
    rollover_sus = Column(Integer, nullable=False)
    withdrawn_sus = Column(Integer, nullable=False)
    current_sus = Column(Integer, nullable=False)
    exhaustion_date = Column(Date, nullable=True)

    account = relationship('Account', back_populates='investments')

    @validates('service_units')
    def _validate_service_units(self, key: str, value: int) -> None:
        super()._validate_service_units(key, value)

    @hybrid_property
    def is_expired(self) -> bool:
        """Return whether the investment is past its end date or is fully withdrawn with no remaining service units"""

        return (self.end_date <= date.today()) or (self.current_sus == 0 and self.withdrawn_sus >= self.service_units)

    @hybrid_property
    def is_active(self) -> bool:
        """Return whether the investment is currently being utilized by the account"""

        today = date.today()
        return (self.start_date <= today) and (today < self.end_date)
