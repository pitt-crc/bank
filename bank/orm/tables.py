"""Object oriented interface for tables in the application database.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date
from logging import getLogger

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates

from .enum import ProposalType
from .mixins import CustomBase
from ..exceptions import MissingProposalError
from ..settings import app_settings
from ..system import SlurmAccount

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
    archived_proposals = relationship('ProposalArchive', back_populates='account')
    archived_investments = relationship('InvestorArchive', back_populates='account')

    def require_proposal(self) -> None:
        """Raise an error if the account does not have a proposal

        Raises:
            MissingProposalError
        """

        if self.proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

    def rollover_investments(self):
        # Renewal, should exclude any previously rolled over SUs
        current_investments = sum(
            get_current_investor_sus_no_rollover(account)
        )

        # If there are relevant investments,
        #     check if there is any rollover
        if current_investments:
            # If current usage exceeds proposal, rollover some SUs, else rollover all SUs
            total_usage = sum([current_usage[c] for c in app_settings.clusters])
            total_proposal_sus = sum([getattr(self.proposal, c) for c in app_settings.clusters])
            if total_usage > total_proposal_sus:
                need_to_rollover = total_proposal_sus + current_investments - total_usage
            else:
                need_to_rollover = current_investments

            # Only half should rollover
            need_to_rollover /= 2

            # If the current usage exceeds proposal + investments or there is no investment, no need to rollover
            if need_to_rollover < 0 or current_investments == 0:
                need_to_rollover = 0

            if need_to_rollover > 0:
                # Go through investments and roll them over
                for inv in self.investments:
                    if need_to_rollover > 0:
                        years_left = inv.end_date.year - date.today().year
                        to_withdraw = (inv.service_units - inv.withdrawn_sus) // years_left
                        to_rollover = int(
                            inv.current_sus
                            if inv.current_sus < need_to_rollover
                            else need_to_rollover
                        )
                        inv.current_sus = to_withdraw
                        inv.rollover_sus = to_rollover
                        inv.withdrawn_sus += to_withdraw
                        need_to_rollover -= to_rollover


class Proposal(Base):
    """Class representation of the ``proposal`` table"""

    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    percent_notified = Column(Integer)
    proposal_type = Column(Enum(ProposalType))

    account = relationship('Account', back_populates='proposal')

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
            account_id=self.account_id,
            start_date=self.start_date,
            end_date=self.end_date,
            proposal_type=self.proposal_type
        )

        slurm_acct = SlurmAccount(self.account)
        for cluster in app_settings.clusters:
            setattr(archive_obj, cluster, getattr(self, cluster))
            setattr(archive_obj, f'{cluster}_usage', slurm_acct.raw_cluster_usage(cluster))

        return archive_obj


class ProposalArchive(Base):
    """Class representation of the ``proposal_archive`` table"""

    __tablename__ = 'proposal_archive'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    proposal_type = Column(Enum(ProposalType))

    account = relationship('Account', back_populates='archived_proposals')

    @validates(*app_settings.clusters, *(f'{c}_usage' for c in app_settings.clusters))
    def validate_service_units(self, key: str, value: int) -> int:
        """Verify the given value is a non-negative integer"""

        if value < 0:
            raise ValueError(f'Invalid value for column {key} - Service units must be a non-negative integer.')

        return value


class Investor(Base):
    """Class representation of the ``investor`` table"""

    __tablename__ = 'investor'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    withdrawn_sus = Column(Integer)
    rollover_sus = Column(Integer)

    account = relationship('Account', back_populates='investments')

    @hybrid_property
    def expired(self) -> bool:
        """Return whether the investment is past its end_date or is fully withdrawn with no remaining service units."""

        return (self.end_date <= date.today()) or (self.current_sus == 0 and self.withdrawn_sus == self.service_units)

    def to_archive_object(self) -> InvestorArchive:
        """Return data from the current row as an ``InvestorArchive`` instance"""

        return InvestorArchive(
            id=self.id,
            account_id=self.account_id,
            start_date=self.start_date,
            end_date=self.end_date,
            exhaustion_date=date.today(),
            service_units=self.service_units,
            current_sus=self.current_sus,
            investor_id=self.id
        )


class InvestorArchive(Base):
    """Class representation of the ``investor_archive`` table"""

    __tablename__ = 'investor_archive'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('account.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    exhaustion_date = Column(Date)
    service_units = Column(Integer)
    current_sus = Column(Integer)

    account = relationship('Account', back_populates='archived_investments')


# Dynamically add columns for each of the managed clusters
for _cluster in app_settings.clusters:
    setattr(Proposal, _cluster, Column(Integer))
    setattr(ProposalArchive, _cluster, Column(Integer))
    setattr(ProposalArchive, f'{_cluster}_usage', Column(Integer))
