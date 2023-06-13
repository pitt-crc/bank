"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper (ORM) for handling database interactions.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, Column, Date, ForeignKey, func, Integer, MetaData, not_, or_, String, create_engine, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, validates

Base = declarative_base()


class Account(Base):
    """User account data

    Table Fields:
      - id  (Integer): Primary key for this table
      - name (String): Unique account name

    Relationships:
      - proposals     (Proposal): One to many
      - investments (Investment): One to many
    """

    __tablename__ = 'account'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    proposals = relationship('Proposal', back_populates='account', cascade="all,delete")
    investments = relationship('Investment', back_populates='account', cascade="all,delete")


class Proposal(Base):
    """Metadata for user proposals

    Table Fields:
      - id                 (Integer): Primary key for this table
      - account_id         (Integer): Primary key for the ``account`` table
      - start_date            (Date): The date when the proposal goes into effect
      - end_date              (Date): The proposal's expiration date
      - percent_notified   (Integer): Percent usage when account holder was last notified

    Relationships:
      - account            (Account): Many to one
      - allocations     (Allocation): One to many

    Hybrid Properties:
        - is_expired       (Boolean): Whether the proposal is expired or not
        - is_active        (Boolean): Whether the proposal is active or not
    """

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(Account.id))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    percent_notified = Column(Integer, nullable=False, default=0)

    account = relationship('Account', back_populates='proposals')
    allocations = relationship('Allocation', back_populates='proposal', cascade="all,delete")

    @validates('percent_notified')
    def _validate_percent_notified(self, key: str, value: int) -> int:
        """Verify the given value is between 0 and 100 (inclusive)

        Args:
            key: Name of the database column being tested
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if 0 <= value <= 100:
            return value

        raise ValueError(f'Value for {key} column must be between 0 and 100 (got {value}).')

    @validates('end_date')
    def _validate_end_date(self, key: str, value: date) -> date:
        """Verify the proposal end date is after the start date

        Args:
            key: Name of the database column being tested
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if self.start_date and value <= self.start_date:
            raise ValueError(f'Value for {key} column must come after the proposal start date')

        return value

    @hybrid_property
    def last_active_date(self) -> date:
        """The last date for which the parent investment is active"""

        return self.end_date - timedelta(days=1)

    @hybrid_property
    def is_expired(self) -> bool:
        """Whether the proposal is past its end date or has exhausted its allocation"""

        # The proposal expired today
        today = date.today()
        if today >= self.end_date:
            return True

        # Proposal has not started yet
        if today < self.start_date:
            return False

        has_allocations = bool(self.allocations)
        has_service_units = not all(alloc.is_exhausted for alloc in self.allocations)

        is_expired = not (has_allocations and has_service_units)

        return is_expired

    @is_expired.expression
    def is_expired(cls) -> bool:
        """SQL expression form of Proposal `is_expired` functionality"""

        today = date.today()

        sub_1 = select(Allocation.proposal_id) \
            .where(Allocation.proposal_id == cls.id) \
            .where(not_(Allocation.is_exhausted))

        # Proposal does not have any active allocations
        sub_2 = select(Proposal.id) \
            .where(today < Proposal.end_date) \
            .where(cls.id.in_(sub_1))

        return and_(today >= Proposal.start_date, not_(cls.id.in_(sub_2)))

    @hybrid_property
    def is_active(self) -> bool:
        """Whether the proposal is within its active date range and has available service units"""

        today = date.today()
        in_date_range = (today >= self.start_date) and (today < self.end_date)

        return in_date_range

    @is_active.expression
    def is_active(cls) -> bool:
        """SQL expression form of Proposal `is_active` functionality"""

        today = date.today()

        sub_1 = select(Proposal.id) \
            .where(and_(today >= cls.start_date, today < cls.end_date))

        return cls.id.in_(sub_1)


class Allocation(Base):
    """Service unit allocations on individual clusters

    Values for the ``service_units_used`` column may exceed the ``service_units_total``
    column in situations where system administrators have bypassed the banking
    system and manually enabled continued usage of a cluster after an allocation
    has run out.

    Table Fields:
      - id                  (Integer): Primary key for this table
      - proposal_id      (ForeignKey): Primary key for the ``proposal`` table
      - cluster_name         (String): Name of the allocated cluster
      - service_units_total (Integer): Number of allocated service units
      - service_units_used  (Integer): Number of used service units

    Relationships:
      - proposal           (Proposal): Many to one

    Hybrid Properties:
        - is_exhausted       (Boolean): Whether the allocation has remaining service units to spend
    """

    __tablename__ = 'allocation'

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(Integer, ForeignKey(Proposal.id))
    cluster_name = Column(String, nullable=False)
    service_units_total = Column(Integer, nullable=False)
    service_units_used = Column(Integer, nullable=False, default=0)

    proposal = relationship('Proposal', back_populates='allocations')

    @validates('service_units_total', 'service_units_used')
    def _validate_service_units(self, key: str, value: int) -> int:
        """Verify whether a numerical value is non-negative

        Args:
            key: Name of the database column being tested
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if value < 0:
            raise ValueError(f'Value for {key} column must be a non-negative integer (got {value}).')

        return value

    @hybrid_property
    def is_exhausted(self) -> bool:
        """Whether the allocation has available service units"""

        return self.service_units_used >= self.service_units_total

    @is_exhausted.expression
    def is_exhausted(cls) -> bool:
        """SQL expression form of Allocation `is_exhausted` functionality"""

        subquery = select(Allocation.id) \
            .where(Allocation.service_units_used >= Allocation.service_units_total)

        return cls.id.in_(subquery)


class Investment(Base):
    """Service unit allocations granted in exchange for user investment

    Table Fields:
      - id            (Integer): Primary key for this table
      - account_id    (Integer): Primary key for the ``account`` table
      - start_date       (Date): Date the investment goes into effect
      - end_date         (Date): Expiration date of the investment
      - service_units (Integer): Total service units granted by an investment
      - rollover_sus  (Integer): Service units carried over from a previous investment
      - withdrawn_sus (Integer): Service units removed from this investment and into another
      - current_sus   (Integer): Total service units available in the investment

    Relationships:
      - account (Account): Many to one

    Hybrid Properties:
        - is_expired       (Boolean): Whether the investment is expired or not
        - is_active        (Boolean): Whether the investment is active or not
    """

    __tablename__ = 'investment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey(Account.id))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    service_units = Column(Integer, nullable=False)
    rollover_sus = Column(Integer, nullable=False, default=0)
    withdrawn_sus = Column(Integer, nullable=False, default=0)
    current_sus = Column(Integer, nullable=False, default=0)

    account = relationship('Account', back_populates='investments')

    @validates('service_units')
    def _validate_service_units(self, key: str, value: int) -> int:
        """Verify whether a numerical value is positive

        Args:
            key: Name of the database column being tested
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if value <= 0:
            raise ValueError(f'Value for {key} columns must be a positive integer (got {value}).')

        return value

    @validates('end_date')
    def _validate_end_date(self, key: str, value: date) -> date:
        """Verify the end date is after the start date

        Args:
            key: Name of the database column being tested
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if self.start_date and value <= self.start_date:
            raise ValueError(f'Value for {key} column must come after the investment start date')

        return value

    @hybrid_property
    def last_active_date(self) -> date:
        """The last date for which the parent investment is active"""

        return self.end_date - timedelta(days=1)

    @hybrid_property
    def is_expired(self) -> bool:
        """Return whether the investment is past its end date or has exhausted its allocation"""

        today = date.today()
        past_end = self.end_date <= today
        started = self.start_date <= today
        spent_service_units = (self.current_sus <= 0) and (self.withdrawn_sus >= self.service_units)
        return past_end or (started and spent_service_units)

    @is_expired.expression
    def is_expired(cls) -> bool:
        """SQL expression form of Investment `is_expired` functionality"""

        today = date.today()

        subquery = select(Investment.id) \
            .where(and_(Investment.current_sus <= 0, Investment.withdrawn_sus >= Investment.service_units)) \
            .where(today >= Investment.start_date)

        return or_(today >= cls.end_date, cls.id.in_(subquery))

    @hybrid_property
    def is_active(self) -> bool:
        """Return if the investment is within its active date range and has available service units"""

        today = date.today()

        in_date_range = (self.start_date <= today) & (today < self.end_date)

        return in_date_range

    @is_active.expression
    def is_active(cls) -> bool:
        """SQL expression form of Investment `is_active` functionality"""

        today = date.today()

        subquery = select(Investment.id) \
            .where(and_(today >= cls.start_date, today < cls.end_date))

        return cls.id.in_(subquery)


class DBConnection:
    """A configurable connection to the application database"""

    connection: Connection = None
    engine: Engine = None
    url: str = None
    metadata: MetaData = Base.metadata
    session = None

    @classmethod
    def configure(cls, url: str) -> None:
        """Update the connection information for the underlying database

        Changes made here will affect the entire running application

        Args:
            url: URL information for the application database
        """

        cls.url = url
        cls.engine = create_engine(cls.url)
        cls.connection = cls.engine.connect()
        cls.session = sessionmaker(cls.engine)
