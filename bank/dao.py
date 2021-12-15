"""The ``dao`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from bisect import bisect_left
from datetime import date, timedelta
from math import ceil
from typing import List, Union

from bank.system import *
from . import settings
from .exceptions import *
from .orm import Investor, Proposal, Session

Numeric = Union[int, float, complex]
LOG = getLogger('bank.cli')


class ProposalServices:
    """Account logic for primary account proposals"""

    def __init__(self, account_name: str) -> None:
        """Manage an existing proposal in the bank

        Args:
            account_name: The name of the account
        """

        self._account_name = account_name

    @property
    def account_name(self) -> str:
        return self._account_name

    @staticmethod
    def _raise_cluster_kwargs(**kwargs: int) -> None:
        """Check whether keyword arguments are valid service unit values

        Args:
            **kwargs: Keyword arguments to check

        Raises:
            ValueError: For an invalid cluster name
            ValueError: For negative service units
        """

        for k, v in kwargs.items():
            if k not in settings.clusters:
                raise ValueError(f'Cluster {k} is not defined in the application settings')

            if v < 0:
                raise ValueError('Service unit values must be greater than zero')

    def _get_proposal_info(self, session: Session) -> Proposal:
        """Return the proposal record from the application database

        Args:
            session: An open database session to use for executing queries

        Returns:
            An entry in the Proposal database

        Raises:
            MissingProposalError: If the account has no associated proposal
        """

        proposal = session.query(Proposal).filter(Proposal.account_name == self._account_name).first()
        if proposal is None:
            raise MissingProposalError(f'Account `{self._account_name}` does not have an associated proposal.')

        return proposal

    def create_proposal(self, start: date = date.today(), duration: int = 365, **kwargs: int) -> None:
        """Create a new proposal for the given account

        Args:
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to add on to each cluster
        """

        with Session() as session:
            if session.query(Proposal).filter(Proposal.account_name == self._account_name).first():
                raise ProposalExistsError(f'Proposal already exists for account: {self._account_name}')

            new_proposal = Proposal(
                account_name=self._account_name,
                percent_notified=0,
                start_date=start,
                end_date=start + timedelta(days=duration),
                **kwargs
            )

            session.add(new_proposal)
            session.commit()
            LOG.info(f"Created proposal {new_proposal.id} for {self._account_name}")

    def delete_proposal(self) -> None:
        """Delete the account's current proposal"""

        with Session() as session:
            proposal = self._get_proposal_info(session)
            session.add(proposal.to_archive_object())
            session.query(Proposal).filter(Proposal.id == proposal.id).delete()
            session.commit()

    def add(self, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal_info(session)

            self._raise_cluster_kwargs(**kwargs)
            for key, val in kwargs.items():
                setattr(proposal, key, getattr(proposal, key) + val)

            session.commit()
            LOG.debug(f"Modified proposal {proposal.id} for account {self._account_name}. Added {kwargs}")

    def subtract(self, **kwargs: int) -> None:
        """Subtract service units from the account's current allocation

        Args:
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal_info(session)

            self._raise_cluster_kwargs(**kwargs)
            for key, val in kwargs.items():
                setattr(proposal, key, getattr(proposal, key) - val)

            session.commit()
            LOG.debug(f"Modified proposal {proposal.id} for account {self._account_name}. Removed {kwargs}")

    def overwrite(self, **kwargs) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal_info(session)

            self._raise_cluster_kwargs(**kwargs)
            for key, val in kwargs.items():
                setattr(proposal, key, val)

            session.commit()
            LOG.debug(f"Modified proposal {proposal.id} for account {self._account_name}. Overwrote {kwargs}")


class InvestmentServices:
    """Data access for investment information associated with a given account"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account
        """

        self.account_name = account_name
        self._raise_if_missing_proposal()

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

    def delete_investment(self, id: int) -> None:
        raise NotImplementedError()

    def add(self, id: int, sus: int) -> None:
        """Add service units to the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to add

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        raise NotImplementedError()

    def subtract(self, id: int, sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to remove

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        raise NotImplementedError()

    def overwrite(self, id: int, sus: int) -> None:
        """Overwrite service units allocated to the given investment

        Args:
            id: The id of the investment to change
            sus: New number of service units to assign to the investment

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        raise NotImplementedError()

    def _get_investment_info(self) -> Tuple[dict, ...]:
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

        if id not in (inv['id'] for inv in self._get_investment_info()):
            raise MissingInvestmentError(f'Account {self.account_name} has no investment with id {id}')

        with Session() as session:
            inv = session.query(Investor).filter(Investor.id == id).first()
            inv.service_units = sus
            session.commit()

        LOG.info(f"Modified Investments for account {self.account_name}: Investment {id} set to {sus}")

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

    def advance(self, sus: int) -> None:
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

    def renew(self, **sus) -> None:
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
            total_usage = sum([current_usage[c] for c in settings.clusters])
            total_proposal_sus = sum([getattr(self.get_proposal_info, c) for c in settings.clusters])
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


class AdminServices:
    """Administration for existing bank accounts"""

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer isinfinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    @staticmethod
    def print_info(account: str) -> None:
        """Print a summary of service units allocated to and used by the account"""

        proposal_info = self._get_proposal_info()
        investment_info = self._get_investment_info()

        # Print the table header
        print(f"|{'-' * 82}|")
        print(f"|{'Proposal End Date':^30}|{proposal_info['end_date'].strftime(settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        allocation_total = 0
        for cluster in settings.clusters:
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

    @staticmethod
    def send_pending_alerts(account: str) -> Optional[EmailMessage]:
        """Send any pending usage alerts to the account

        Returns:
            If an alert is sent, returns a copy of the email alert
        """

        proposal = self._get_proposal_info()

        # Determine the next usage percentage that an email is scheduled to be sent out
        usage = sum(self.get_cluster_usage(c) for c in settings.clusters())
        allocated = sum(proposal[c] for c in settings.clusters)
        usage_perc = int(usage / allocated * 100)
        next_notify = settings.notify_levels[bisect_left(settings.notify_levels, usage_perc)]

        email = None
        end_date = proposal['end_date'].strftime(settings.date_format)
        days_until_expire = (proposal['end_date'] - date.today()).days
        if days_until_expire in settings.warning_days:
            email = EmailTemplate(settings.expiration_warning)
            subject = f'Your proposal expiry reminder for account: {self._account_name}'

        elif days_until_expire == 0:
            email = EmailTemplate(settings.expired_proposal_notice)
            subject = f'The account for {self._account_name} was locked because it reached the end date {end_date}'

        elif proposal['percent_notified'] < next_notify <= usage_perc:
            with Session() as session:
                db_entry = session.query(Proposal).filter(Proposal.account_name == self._account_name).first()
                db_entry.percent_notified = next_notify
                session.commit()

            email = EmailTemplate(settings.usage_warning.format(perc=usage_perc))
            subject = f"Your account {self._account_name} has exceeded a proposal threshold"

        if email:
            formatted = email.format(
                account=self._account_name,
                start_date=proposal['start_date'].strftime(settings.date_format),
                end_date=end_date,
                perc=usage_perc,
                exp_in_days=days_until_expire
            )
            return formatted.send_to(f'{self._account_name}{settings.email_suffix}', subject=subject)

    @staticmethod
    def find_unlocked() -> Tuple[str]:
        """Return the names for all unexpired proposals with unlocked accounts

        Returns:
            A tuple of account names
        """

        # Query database for accounts that are unlocked and expired
        with Session() as session:
            proposals: List[Proposal] = session.query(Proposal).filter((Proposal.end_date < date.today())).all()
            return tuple(p.account_name for p in proposals if not SlurmAccount(p.account_name).get_locked_state())
