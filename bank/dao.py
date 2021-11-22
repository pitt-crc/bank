"""The ``dao`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

Usage Example
-------------

The ``Account`` class is used as the primary administration tool to manage new
and existing user accounts. For example:

.. code-block:: python

  >>> from bank.dao import Account
  >>>
  >>> # Create an account with a new proposal
  >>> account = Account('account_name')
  >>> account.create_proposal(cluster_name=1000)
  >>>
  >>> # Add service units to a proposal
  >>> account.add_allocation_sus(cluster_name=500)
  >>>
  >>> # Lock the user account from running any more jobs
  >>> account.set_locked_state(lock_state=True)

API Reference
-------------
"""

from bisect import bisect_left
from datetime import date, timedelta
from email.message import EmailMessage
from logging import getLogger
from typing import List, Tuple, Union, Optional

from math import ceil

from bank.exceptions import MissingProposalError, ProposalExistsError, MissingInvestmentError
from bank.orm import Investor, Proposal, Session
from bank.orm.enum import ProposalType
from bank.settings import app_settings
from bank.system import SlurmAccount, EmailTemplate

Numeric = Union[int, float, complex]
LOG = getLogger('bank.cli')


class ProposalData:
    """Data access for proposal information associated with a given account"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account
        """

        self.account_name = account_name

    def create_proposal(self, ptype: str = 'PROPOSAL', **sus_per_cluster: int) -> None:
        """Create a new proposal for the given account

        Args:
            ptype: The type of proposal
            **sus_per_cluster: Service units to add on to each cluster
        """

        proposal_type = ProposalType[ptype.upper()]

        proposal_duration = timedelta(days=365)
        start_date = date.today()

        with Session() as session:
            # Make sure proposal does not already exist
            if session.query(Proposal).filter(Proposal.account_name == self.account_name).first():
                raise ProposalExistsError(f'Proposal already exists for account: {self.account_name}')

            new_proposal = Proposal(
                account_name=self.account_name,
                proposal_type=proposal_type,
                percent_notified=0,
                start_date=start_date,
                end_date=start_date + proposal_duration,
                **sus_per_cluster
            )

            session.add(new_proposal)
            session.commit()

        sus_as_str = ', '.join(f'{k}={v}' for k, v in sus_per_cluster.items())
        LOG.info(f"Inserted proposal with type {proposal_type.name} for {self.account_name} with {sus_as_str}")

    def get_proposal_info(self) -> dict:
        """Information about the primary account proposal

        Returns:
            Properties of the account's proposal as a dictionary

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            if proposal is None:
                raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

            return proposal.row_to_dict()

    def add_allocation_sus(self, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            **kwargs: Service units to add to the account for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        proposal_info = self.get_proposal_info()
        new_allocation = dict()
        for cluster, sus_to_add in kwargs.items():
            if sus_to_add < 0:
                raise ValueError(f'Cannot add negative service units (received {sus_to_add} for {cluster})')

            new_allocation[cluster] = proposal_info.get(cluster, 0) + sus_to_add

        self.overwrite_allocation_sus(**new_allocation)
        LOG.debug(f"Added SUs to proposal for {self.account_name}, new limits are {new_allocation}")

    def overwrite_allocation_sus(self, **kwargs) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            **kwargs: New service unit values for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            if proposal is None:
                raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

            for cluster, service_units in kwargs.items():
                if cluster not in app_settings.clusters:
                    raise ValueError(f'Cluster {cluster} is not defined in application settings.')

                setattr(proposal, cluster, service_units)

            session.commit()

        LOG.info(f"Changed proposal for {self.account_name} to {self.get_proposal_info()}")


class InvestorData(SlurmAccount):
    """Data access for investment information associated with a given account"""

    def _raise_if_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception if the account does not have a primary proposal"""

        with Session() as session:
            proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            if proposal is None:
                raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

    def create_investment(self, sus: int) -> None:
        """Add a new investor proposal for the given account

        Args:
            sus: The number of service units to add
        """

        self._raise_if_missing_proposal()
        start_date = date.today()
        end_date = start_date + timedelta(days=5 * 365)  # Investor accounts last 5 years
        new_investor = Investor(
            account_name=self.account_name,
            start_date=start_date,
            end_date=end_date,
            service_units=sus,
            current_sus=ceil(sus / 5),
            withdrawn_sus=0,
            rollover_sus=0
        )

        with Session() as session:
            session.add(new_investor)
            session.commit()

        LOG.info(f"Inserted investment for {self.account_name} with per year allocations of `{sus}`")

    def get_investment_info(self) -> Tuple[dict, ...]:
        """Tuple with information for each investment associated with the account"""

        with Session() as session:
            investments = session.query(Investor).filter(Investor.account_name == self.account_name).all()
            return tuple(inv.row_to_dict() for inv in investments)

    def overwrite_investment_sus(self, id: int, sus: int) -> None:
        """Replace the number of service units allocated to a given investment

        Args:
            id: The id of the investment to change
            sus: New service units to set in the investment
        """

        if id not in (inv['id'] for inv in self.get_investment_info()):
            raise MissingInvestmentError(f'Account {self.account_name} has no investment with id {id}')

        with Session() as session:
            inv = session.query(Investor).filter(Investor.id == id).first()
            inv.service_units = sus
            session.commit()

        LOG.info(f"Modified Investments for account {self.account_name}: Investment {id} set to {sus}")

    def renewal(self, **sus) -> None:
        with Session() as session:
            self.proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            self._investments = session.query(Investor).filter(Investor.account_name == self.account_name).first()

            # Move the old account proposal to the archive table
            session.add(self.get_proposal_info.to_archive_object())
            self.get_proposal_info.proposal.delete()

            # Move any expired investments to the archive table
            for investment in self._investments.get_investment_info:
                if investment.expired:
                    session.add(investment.to_archive_obj())
                    investment.delete()

            # Add new proposal and rollover investment service units
            self.proposal = Proposal(**sus)
            self._rollover_investments()
            session.commit()

        # Set RawUsage to zero and unlock the account
        self.reset_raw_usage()
        self.set_locked_state(False)

    def _rollover_investments(self):
        # Renewal, should exclude any previously rolled over SUs
        current_investments = sum(inv.current_sus for inv in self._investments)

        # If there are relevant investments,
        #     check if there is any rollover
        if current_investments:
            # If current usage exceeds proposal, rollover some SUs, else rollover all SUs
            total_usage = sum([current_usage[c] for c in app_settings.clusters])
            total_proposal_sus = sum([getattr(self.get_proposal_info, c) for c in app_settings.clusters])
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
                for inv in self._investments:
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

    def _withdraw_from_investment(self, investment: Investor, sus: int) -> int:
        """Process the withdrawal for a single investment

        The returned number of service units may be less than the requested
        withdrawal if there are insufficient service units in the account balance.
        The ``investment`` argument is mutated to reflect the withdrawal, but no
         commits are made to the database by this method.

        Args:
            investment: The investment to withdraw from
            sus: The requested number of service units to withdraw

        Returns:
            The number of service units that were actually withdrawn
        """

        if sus <= 0:
            raise ValueError('Withdrawal amount must be greater than zero')

        maximum_withdrawal = investment.service_units - investment.withdrawn_sus
        to_withdraw = min(sus, maximum_withdrawal)
        investment.current_sus += to_withdraw
        investment.withdrawn_sus += to_withdraw

        msg = f"Withdrew {to_withdraw} service units from investment {investment.id} for account {self.account_name}"
        LOG.info(msg)
        print(msg)

        return to_withdraw

    def withdraw(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        with Session() as session:
            investments = session.query(Investor) \
                .filter(Investor.account_name == self.account_name) \
                .order_by(Investor.start_date) \
                .all()

            # Make sure there are enough service units in the account to withdraw
            available_sus = sum(inv.service_units - inv.withdrawn_sus for inv in investments)
            if sus > available_sus:
                raise ValueError(f"Requested to withdraw {sus} but the account only has {available_sus} SUs available.")

            # Go through investments, oldest first and start withdrawing
            investment: Investor
            for investment in investments:
                withdrawn = self._withdraw_from_investment(investment, sus)

                # Determine if we are done processing investments
                sus -= withdrawn
                if sus <= 0:
                    break

            LOG.debug('Committing withdrawals to database')
            session.commit()


class Account(ProposalData, InvestorData):
    """Administration for existing bank accounts"""

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer isinfinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def print_allocation_info(self) -> None:
        """Print proposal information for the account"""

        with Session() as session:
            proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            investments = session.query(Investor).filter(Investor.account_name == self.account_name).all()

            if proposal is None:
                raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

            print(proposal.row_to_ascii_table())
            for inv in investments:
                print(inv.row_to_ascii_table())

    def print_usage_info(self) -> None:
        """Print a summary of service units used by the given account"""

        proposal_info = self.get_proposal_info()
        investment_info = self.get_investment_info()

        # Print the table header
        print(f"|{'-' * 82}|")
        print(f"|{'Proposal End Date':^30}|{proposal_info['end_date'].strftime(app_settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        allocation_total = 0
        for cluster in app_settings.clusters:
            usage = self.get_cluster_usage(cluster, in_hours=True)
            allocation = proposal_info[cluster]
            percentage = round(self._calculate_percentage(usage, allocation), 2) or 'N/A'
            print(f"|{'-' * 82}|\n"
                  f"|{'Cluster: ' + cluster + ', Available SUs: ' + str(allocation) :^82}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'Overall':^20}|{usage:^30d}|{percentage:^30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")

            usage_total += usage
            allocation_total += allocation

        usage_percentage = self._calculate_percentage(usage_total, allocation_total)
        investment_total = sum(inv['service_units'] for inv in investment_info)
        investment_percentage = self._calculate_percentage(usage_total, allocation_total + investment_total)

        # Print usage information concerning investments
        print(f"|{'Aggregate':^82}|")
        print("|{'-' * 40:^40}|{'-' * 41:^41}|")

        if investment_total == 0:
            print(f"|{'Aggregate Usage':^40}|{usage_percentage:^41.2f}|")
            print(f"|{'-' * 82}|")

        else:
            print(f"|{'Investments Total':^40}|{str(investment_total) + '^a':^41}|\n"
                  f"|{'Aggregate Usage (no investments)':^40}|{usage_percentage:^41.2f}|\n"
                  f"|{'Aggregate Usage':^40}|{investment_percentage:^41.2f}|\n"
                  f"|{'-' * 40:^40}|{'-' * 41:^41}|\n"
                  f"|{'^a Investment SUs can be used across any cluster':^82}|\n"
                  f"|{'-' * 82}|")

    def send_pending_alerts(self) -> Optional[EmailMessage]:
        """Send any pending usage alerts to the account

        Returns:
            If an alert is sent, returns a copy of the email alert
        """

        proposal = self.get_proposal_info()

        # Determine the next usage percentage that an email is scheduled to be sent out
        usage = sum(self.get_cluster_usage(c) for c in app_settings.clusters())
        allocated = sum(proposal[c] for c in app_settings.clusters)
        usage_perc = int(usage / allocated * 100)
        next_notify = app_settings.notify_levels[bisect_left(app_settings.notify_levels, usage_perc)]

        email = None
        end_date = proposal['end_date'].strftime(app_settings.date_format)
        days_until_expire = (proposal['end_date'] - date.today()).days
        if days_until_expire in app_settings.warning_days:
            email = EmailTemplate(app_settings.expiration_warning)
            subject = f'Your proposal expiry reminder for account: {self.account_name}'

        elif days_until_expire == 0:
            email = EmailTemplate(app_settings.expired_proposal_notice)
            subject = f'The account for {self.account_name} was locked because it reached the end date {end_date}'

        elif proposal['percent_notified'] < next_notify <= usage_perc:
            with Session() as session:
                db_entry = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
                db_entry.percent_notified = next_notify
                session.commit()

            email = EmailTemplate(app_settings.usage_warning.format(perc=usage_perc))
            subject = f"Your account {self.account_name} has exceeded a proposal threshold"

        if email:
            formatted = email.format(
                account=self.account_name,
                start_date=proposal['start_date'].strftime(app_settings.date_format),
                end_date=end_date,
                perc=usage_perc
            )
            return formatted.send_to(f'{self.account_name}{app_settings.email_suffix}', subject=subject)

    @staticmethod
    def find_unlocked() -> Tuple[str]:
        """Return the names for all unexpired proposals with unlocked accounts

        Returns:
            A tuple of account names
        """

        # Query database for accounts that are unlocked and expired
        with Session() as session:
            proposals: List[Proposal] = session.query(Proposal).filter((Proposal.end_date < date.today())).all()
            return tuple(p.account_name for p in proposals if not Account(p.account_name).get_locked_state())
