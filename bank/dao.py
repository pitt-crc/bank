"""The ``dao`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

Usage Example
-------------

The ``Account`` class is used to administrate existing user accounts
with established proposals. For example:

.. code-block:: python

  >>> from bank.dao import Account
  >>>
  >>> # Lock the user account from running any more jobs
  >>> account = Account('account_name')
  >>> account.set_locked_state(lock_state=True)

The ``Bank`` class is used to create new accounts/proposals/investments and
to handle bank wide tasks that aren't specific to a single user. For example:

.. code-block:: python

  >>> from bank.dao import Account
  >>>
  >>> # List all unlocked accounts
  >>> unlocked_accounts = Bank().find_unlocked()

API Reference
-------------
"""

from bisect import bisect_left
from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import List, Tuple, Dict, Any, Union

from bank.exceptions import MissingProposalError
from bank.orm import Investor, Proposal, Session
from bank.orm.enum import ProposalType
from bank.settings import app_settings
from bank.system import SlurmAccount

Numeric = Union[int, float, complex]
LOG = getLogger('bank.cli')


class Account(SlurmAccount):
    """Administration for existing bank accounts"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account

        Raises:
            MissingProposalError: If the account does not exist
        """

        super().__init__(account_name)
        self.account_name = account_name

        # We cache the current proposal and investment data to make method calls faster
        # Note that changes to cached values will not propagate into the database
        with Session() as session:
            self._proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            self._investments = session.query(Investor).filter(Investor.account_name == self.account_name).all()

        if self._proposal is None:
            raise MissingProposalError(f'Account `{self.account_name}` does not have an associated proposal.')

    def print_allocation_info(self) -> None:
        """Print proposal information for the account"""

        # Print all database entries associate with the account as an ascii table
        print(self._proposal.row_to_ascii_table())
        for inv in self._investments:
            print(inv.row_to_ascii_table())

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer isinfinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def print_usage_info(self) -> None:
        """Print a summary of service units used by the given account"""

        # Print the table header
        print(f"|{'-' * 82}|")
        print(f"|{'Proposal End Date':^30}|{self._proposal.end_date.strftime(app_settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        allocation_total = 0
        for cluster in app_settings.clusters:
            usage = self.get_cluster_usage(cluster, in_hours=True)
            allocation = getattr(self._proposal, cluster)
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

        # Calculate usage percentages while being careful not to divide by zero
        usage_percentage = self._calculate_percentage(usage_total, allocation_total)

        investment_total = sum(inv.sus for inv in self._investments)
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

    def get_cluster_allocation(self) -> Dict[str, int]:
        """Return the number of service units allocated to the user on each cluster

        Returns:
            Dictionary of cluster names and allocated service units
        """

        return {c: getattr(self._proposal, c) for c in app_settings.clusters}

    def set_cluster_allocation(self, **kwargs) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            **kwargs: New service unit values for each cluster
        """

        with Session() as session:
            self._proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            for cluster, service_units in kwargs.items():
                if cluster not in app_settings.clusters:
                    raise ValueError(f'Cluster {cluster} is not defined in application settings.')

                setattr(self._proposal, cluster, service_units)

            session.commit()

        LOG.info(f"Changed proposal for {self.account_name} to {self.get_cluster_allocation()}")

    def add_allocation_sus(self, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            **kwargs: Service units to add to the account for each cluster
        """

        current_sus = self.get_cluster_allocation()
        for key in kwargs:
            kwargs[key] += current_sus.get(key, 0)

        self.set_cluster_allocation(**current_sus)
        LOG.debug(f"Added SUs to proposal for {self.account_name}, new limits are {current_sus}")

    def get_investment_sus(self) -> Dict[str, int]:
        """Return a dictionary with the number of service units for each investment tied to the account"""

        return {str(inv.id): inv.sus for inv in self._investments}

    def set_investment_sus(self, **kwargs: int) -> None:
        """Replace the number of service units allocated to a given investment

        Args:
            **kwargs: New service unit values to set in each investment
        """

        investment_ids = {str(inv.id) for inv in self._investments}
        invalid_ids = set(kwargs) - investment_ids
        if invalid_ids:
            raise ValueError(f'Account {self.account_name} has no investment with ids {invalid_ids}')

        with Session() as session:
            self._investments = session.query(Investor).all()
            for inv in self._investments:
                inv.sus = kwargs.get(str(inv.id), 0)

            session.commit()

        LOG.info(f"Modified Investments for account{self.account_name}: {kwargs}")

    def renewal(self, **sus) -> None:
        with Session() as session:
            self._proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
            self._investments = session.query(Investor).filter(Investor.account_name == self.account_name).first()

            # Move the old account proposal to the archive table
            session.add(self._proposal.to_archive_object())
            self._proposal.proposal.delete()

            # Move any expired investments to the archive table
            for investment in self._investments.investments:
                if investment.expired:
                    session.add(investment.to_archive_obj())
                    investment.delete()

            # Add new proposal and rollover investment service units
            self._proposal = Proposal(**sus)
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
            total_proposal_sus = sum([getattr(self._proposal, c) for c in app_settings.clusters])
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

    def withdraw(self, sus: int) -> None:
        """Withdraw service units from future investments and allocate to the current proposal

        Args:
            sus: The number of service units to withdraw
        """

        with Session() as session:
            self._investments = session.query(Investor).filter(Investor.account_name == self.account_name).first()
            available_investments = sum(inv.service_units - inv.withdrawn_sus for inv in self._investments)

            if sus > available_investments:
                print(f"Requested to withdraw {sus} but the account only has {available_investments} SUs to withdraw!")
                return

            # Go through investments, oldest first and start withdrawing
            for investment in enumerate(self._investments):
                # If no SUs available to withdraw, skip the proposal entirely
                investment_remaining = investment.service_units - investment.withdrawn_sus
                if investment_remaining <= 0:
                    print(f"No service units can be withdrawn from investment {investment['id']}")
                    continue

                # Determine what we can withdraw from current investment
                to_withdraw = min(sus, investment_remaining)
                investment.current_sus += to_withdraw
                investment.withdrawn_sus += to_withdraw
                sus -= to_withdraw

                msg = f"Withdrew {to_withdraw} service units from investment {investment.id} for account {self.account_name}"
                LOG.info(msg)
                print(msg)

                # Determine if we are done processing investments
                if sus <= 0:
                    break

            session.commit()

    def send_pending_alerts(self) -> None:
        """Send any pending usage alerts to the account"""

        # Determine the next usage percentage that an email is scheduled to be sent out
        usage = sum(self.get_cluster_usage(c) for c in app_settings.clusters())
        allocated = sum(self.get_cluster_allocation().values())
        usage_perc = int(usage / allocated * 100)
        next_notify = app_settings.notify_levels[bisect_left(app_settings.notify_levels, usage_perc)]

        days_until_expire = (self._proposal.end_date - date.today()).days
        if days_until_expire in app_settings.warning_days:
            self.notify(app_settings.three_month_proposal_expiry_notification)

        elif days_until_expire == 0:
            self.set_locked_state(True)
            self.notify(app_settings.proposal_expires_notification)
            LOG.info(
                f"The account for {self.account_name} was locked because it reached the end date {self._proposal.end_date.strftime(app_settings.date_format)}")

        elif self._proposal.percent_notified < next_notify <= usage_perc:
            with Session() as session:
                self._proposal = session.query(Proposal).filter(Proposal.account_name == self.account_name).first()
                self._proposal.percent_notified = next_notify
                session.commit()

            self.notify(app_settings.notify_sus_limit_email_text)

    def notify(self, email_template):
        raise NotImplementedError


class Bank:
    """Handles the creation of new accounts in the banking system"""

    @staticmethod
    def find_unlocked() -> Tuple[str]:
        """Return the names for all unexpired proposals with unlocked accounts

        Returns:
            A tuple of account names
        """

        # Query database for accounts that are unlocked and expired
        with Session() as session:
            proposals: List[Proposal] = session.query(Proposal).filter(
                (Proposal.end_date < date.today()) and (not Proposal.account.locked_state)
            ).all()

        return tuple(p.account_name for p in proposals)

    @staticmethod
    def create_proposal(account: str, ptype: str, **sus_per_cluster: int) -> None:
        """Create a new proposal for the given account

        Args:
            account: The account name to add a proposal for
            ptype: The type of proposal
            **sus_per_cluster: Service units to add on to each cluster
        """

        proposal_type = ProposalType[ptype.upper()]
        proposal_duration = timedelta(days=365)
        start_date = date.today()
        new_proposal = Proposal(
            account_name=account,
            proposal_type=proposal_type,
            percent_notified=0,
            start_date=start_date,
            end_date=start_date + proposal_duration,
            **sus_per_cluster
        )

        with Session() as session:
            session.add(new_proposal)
            session.commit()

        sus_as_str = ', '.join(f'{k}={v}' for k, v in sus_per_cluster.items())
        LOG.info(f"Inserted proposal with type {proposal_type.name} for {account} with {sus_as_str}")

    @staticmethod
    def create_investment(account, sus: int) -> None:
        """Add a new investor proposal for the given account

        Args:
            account: The account name to add a proposal for
            sus: The number of service units to add
        """

        start_date = date.today()
        end_date = start_date + timedelta(days=5 * 365)  # Investor accounts last 5 years
        new_investor = Investor(
            account_name=account,
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

        LOG.info(f"Inserted investment for {account} with per year allocations of `{sus}`")
