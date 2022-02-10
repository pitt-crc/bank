"""The ``dao`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import List, Union, Tuple

from . import settings
from .exceptions import *
from .orm import Investor, Proposal, Session
from .system import SlurmAccount

Numeric = Union[int, float, complex]
LOG = getLogger('bank.dao')


class BaseDataAccess:
    """Base class for building data access objects"""

    def __init__(self, account_name: str) -> None:
        """Manage an existing proposal in the bank

        Args:
            account_name: The name of the account
        """

        self._account_name = account_name
        self._slurm_acct = SlurmAccount(account_name)

    @property
    def account_name(self) -> str:
        return self._account_name

    def _get_proposal(self, session: Session = None) -> Proposal:
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

    def _get_investment(self, session: Session, id: int = None) -> Union[Investor, List[Investor]]:
        """Return any investments associated with the account from the application database

        Args:
            session: An open database session to use for executing queries
            id: Optionally return a single investment with the given id instead of all investments

        Returns:
            One or more entries in the Investment Database
        """

        if id:
            inv = session.query(Investor).filter(Investor.account_name == self._account_name, Investor.id == id).first()
            error = f'Account {self.account_name} has no investment with id {id}'

        else:
            inv = session.query(Investor).filter(Investor.account_name == self._account_name).order_by(Investor.start_date).all()
            error = f'Account {self.account_name} has no associated investments'

        if not inv:
            raise MissingInvestmentError(error)

        return inv


class ProposalServices(BaseDataAccess):
    """Account logic for primary account proposals"""

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
                raise ValueError(f'Service unit values cannot be negative (got value: {v})')

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

            self._raise_cluster_kwargs(**kwargs)
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
            proposal = self._get_proposal(session)
            session.add(proposal.to_archive_object())
            session.query(Proposal).filter(Proposal.id == proposal.id).delete()
            session.commit()

        LOG.info(f"Deleted proposal {proposal.id} for {self._account_name}")

    def add(self, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal(session)

            self._raise_cluster_kwargs(**kwargs)
            for key, val in kwargs.items():
                setattr(proposal, key, getattr(proposal, key) + val)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Added {kwargs}")

    def subtract(self, **kwargs: int) -> None:
        """Subtract service units from the account's current allocation

        Args:
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal(session)

            self._raise_cluster_kwargs(**kwargs)
            for key, val in kwargs.items():
                setattr(proposal, key, getattr(proposal, key) - val)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Removed {kwargs}")

    def overwrite(self, start_date: date = None, end_date: date = None, **kwargs) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            start_date: Optionally set a new start date for the proposal
            end_date: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with Session() as session:
            proposal = self._get_proposal(session)

            self._raise_cluster_kwargs(**kwargs)
            kwargs['start_date'] = start_date or proposal.start_date
            kwargs['end_date'] = end_date or proposal.end_date

            for key, val in kwargs.items():
                setattr(proposal, key, val)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Overwrote {kwargs}")


class InvestmentServices(BaseDataAccess):
    """Data access for investment information associated with a given account"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account
        """

        super().__init__(account_name)
        with Session() as session:
            # Raise an error if there is no user proposal
            self._get_proposal(session)

    @staticmethod
    def _raise_invalid_sus(sus: int) -> None:
        """Check whether the given value is a valid service unit

        Args:
            sus: The value to check

        Raises:
            ValueError: If the given value is not greater than zero
        """

        if sus <= 0:
            raise ValueError('Service units must be greater than zero.')

    def create_investment(self, sus: int, start: date = date.today(), duration: int = 365, num_inv=1) -> None:
        """Add a new investment(s) for the given account

        ``num_inv`` reflects the number of investments to create. If the argument
        is greater than one, repeating investments are created sequentially such
        that a new investment begins as each investment ends. The ``start``
        argument represents the start date of the first investment in the sequence.
        The given number of service units (``sus``) are allocated equally across
        each investment in the series.

        Args:
            sus: The number of service units to add
            start: The start date of the proposal
            duration: How many days before the investment expires
            num_inv: Spread out the given service units equally across given number of instances
        """

        if num_inv < 1:
            raise ValueError('Argument ``repeat`` must be >= 1')

        # Calculate number of service units per each investment
        duration = timedelta(days=duration)
        sus_per_instance = ceil(sus / num_inv)
        self._raise_invalid_sus(sus_per_instance)

        with Session() as session:
            self._get_proposal(session)

            for i in range(num_inv):
                start_this = start + i * duration
                end_this = start + (i + 1) * duration

                new_investor = Investor(
                    account_name=self._account_name,
                    start_date=start_this,
                    end_date=end_this,
                    service_units=sus_per_instance,
                    current_sus=sus_per_instance,
                    withdrawn_sus=0,
                    rollover_sus=0
                )

                session.add(new_investor)
                LOG.debug(f"Inserting investment {new_investor.id} for {self._account_name} with allocation of `{sus}`")

            session.commit()

        LOG.info(f"Invested {sus} service units for account {self._account_name}")

    def delete_investment(self, id: int) -> None:
        """Delete one of the account's associated investments

        Args:
            id: The id of the investment to delete
        """

        with Session() as session:
            investment = self._get_investment(session, id)
            session.add(investment.to_archive_object())
            session.query(Investor).filter(Investor.id == investment.id).delete()
            session.commit()

        LOG.info(f'Archived investment {investment.id} for account {self._account_name}')

    def add(self, id: int, sus: int) -> None:
        """Add service units to the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to add

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._raise_invalid_sus(sus)
        with Session() as session:
            investment = self._get_investment(session, id)
            investment.service_units += sus
            investment.current_sus += sus
            session.commit()

        LOG.info(f'Added {sus} service units to investment {investment.id} for account {self._account_name}')

    def subtract(self, id: int, sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to remove

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._raise_invalid_sus(sus)
        with Session() as session:
            investment = self._get_investment(session, id)
            if investment.current_sus < sus:
                raise ValueError(f'Cannot subtract {sus}. Investment {id} only has {investment.current_sus} available.')

            investment.service_units -= sus
            investment.current_sus -= sus
            session.commit()

        LOG.info(f'Removed {sus} service units to investment {investment.id} for account {self._account_name}')

    def overwrite(self, id: int, sus: int, start_date: date = None, end_date: date = None, ) -> None:
        """Overwrite service units allocated to the given investment

        Args:
            id: The id of the investment to change
            sus: New number of service units to assign to the investment

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._raise_invalid_sus(sus)
        with Session() as session:
            investment = self._get_investment(session, id)
            investment.service_units = sus

            if start_date:
                investment.start_date = start_date

            if end_date:
                investment.start_date = end_date

            session.commit()

        LOG.info(f'Overwrote service units on investment {investment.id} to {sus} for account {self._account_name}')

    def advance(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        self._raise_invalid_sus(sus)
        requested_withdrawal = sus

        with Session() as session:
            # Query all of the account's investments from the database and sort them
            # so that younger investments (i.e., with later start dates) come first
            investments = session.query(Investor) \
                .filter(Investor.account_name == self._account_name) \
                .order_by(Investor.start_date.desc()) \
                .all()

            if len(investments) < 2:
                raise MissingInvestmentError(f'Account has {len(investments)} investments, but must have at least 2 to process an advance.')

            *young_investments, oldest_investment = investments
            if not (oldest_investment.start_date <= date.today() or date.today() < oldest_investment.end_date):
                raise MissingInvestmentError(f'Account does not have a currently active investment to advance into.')

            available_sus = sum(inv.service_units - inv.withdrawn_sus for inv in investments)
            if sus > available_sus:
                raise ValueError(f"Requested to withdraw {sus} but the account only has {available_sus} SUs available.")

            # Move service units from younger investments to the oldest available investment
            for investment in young_investments:
                maximum_withdrawal = investment.service_units - investment.withdrawn_sus
                to_withdraw = min(sus, maximum_withdrawal)

                LOG.info(f'Withdrawing {to_withdraw} service units from investment {investment.id}')
                investment.current_sus -= to_withdraw
                investment.withdrawn_sus += to_withdraw
                oldest_investment.current_sus += to_withdraw

                # Check if we have withdrawn the requested number of service units
                sus -= to_withdraw
                if sus <= 0:
                    break

            session.commit()

        LOG.info(f'Advanced {requested_withdrawal - sus} service units for account {self._account_name}')


class AdminServices(BaseDataAccess):
    """Administration for existing bank accounts"""

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def _build_usage_str(self):
        """Return a human-readable summary of the accounts allocations"""

        with Session() as session:
            proposal = self._get_proposal(session)
            try:
                investments = self._get_investment(session)

            except MissingInvestmentError:
                investments = []

        # The table header
        output_lines = []
        output_lines.append(f"|{'-' * 82}|")
        output_lines.append(f"|{'Proposal End Date':^30}|{proposal.end_date.strftime(settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        allocation_total = 0
        for cluster in settings.clusters:
            usage = self._slurm_acct.get_cluster_usage(cluster, in_hours=True)
            allocation = getattr(proposal, cluster)
            percentage = round(self._calculate_percentage(usage, allocation), 2) or 'N/A'
            output_lines.append(f"|{'-' * 82}|")
            output_lines.append(f"|{'Cluster: ' + cluster + ', Available SUs: ' + str(allocation) :^82}|")
            output_lines.append(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")
            output_lines.append(f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|")
            output_lines.append(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")
            output_lines.append(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")
            output_lines.append(f"|{'Overall':^20}|{usage:^30d}|{percentage:^30}|")
            output_lines.append(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")

            usage_total += usage
            allocation_total += allocation

        usage_percentage = self._calculate_percentage(usage_total, allocation_total)
        investment_total = sum(inv.service_units for inv in investments)
        investment_percentage = self._calculate_percentage(usage_total, allocation_total + investment_total)

        # Print usage information concerning investments
        output_lines.append(f"|{'Aggregate':^82}|")
        output_lines.append(f"|{'-' * 40:^40}|{'-' * 41:^41}|")

        if investment_total == 0:
            output_lines.append(f"|{'Aggregate Usage':^40}|{usage_percentage:^41.2f}|")
            output_lines.append(f"|{'-' * 82}|")

        else:
            output_lines.append(f"|{'Investments Total':^40}|{str(investment_total) + '^a':^41}|")
            output_lines.append(f"|{'Aggregate Usage (no investments)':^40}|{usage_percentage:^41.2f}|")
            output_lines.append(f"|{'Aggregate Usage':^40}|{investment_percentage:^41.2f}|")
            output_lines.append(f"|{'-' * 40:^40}|{'-' * 41:^41}|")
            output_lines.append(f"|{'^a Investment SUs can be used across any cluster':^82}|")
            output_lines.append(f"|{'-' * 82}|")

        return '\n'.join(output_lines)

    def _build_investment_str(self) -> str:
        """Return a human-readable summary of the account's investments

        The returned string is empty if there are no investments
        """
        with Session() as session:
            try:
                investments = self._get_investment(session)

            except MissingInvestmentError:
                return ''

        output_lines = [
            '|--------------------------------------------------------------------------------|',
            '| Total Investment SUs | Start Date | Current SUs | Withdrawn SUs | Rollover SUs |',
            '|--------------------------------------------------------------------------------|',
        ]
        for inv in investments:
            output_lines.append(f"| {inv.service_units:20} | {inv.start_date.strftime(settings.date_format):>10} | {inv.current_sus:11} | {inv.withdrawn_sus:13} | {inv.withdrawn_sus:12} |")

        output_lines.append('|--------------------------------------------------------------------------------|')
        return '\n'.join(output_lines)

    def print_info(self) -> None:
        """Print a summary of service units allocated to and used by the account"""

        print(self._build_usage_str())
        print(self._build_investment_str())

    def notify_account(self) -> None:
        """Send any pending usage alerts to the account"""

        with Session() as session:
            proposal = self._get_proposal(session)

            # Determine the next usage percentage that an email is scheduled to be sent out
            usage = self._slurm_acct.get_total_usage()
            allocated = proposal.total_allocated
            usage_perc = min(int(usage / allocated * 100), 100)
            next_notify_perc = next((perc for perc in sorted(settings.notify_levels) if perc >= usage_perc), 100)

            email = None
            days_until_expire = (proposal.end_date - date.today()).days
            if days_until_expire == 0:
                email = settings.expired_proposal_notice
                subject = f'The account for {self._account_name} has reached its end date'
                self._slurm_acct.set_locked_state(True)

            elif days_until_expire in settings.warning_days:
                email = settings.expiration_warning
                subject = f'Your proposal expiry reminder for account: {self._account_name}'

            elif proposal.percent_notified < next_notify_perc <= usage_perc:
                proposal.percent_notified = next_notify_perc
                email = settings.usage_warning
                subject = f"Your account {self._account_name} has exceeded a proposal threshold"

            if email:
                email.format(
                    account_name=self.account_name,
                    start_date=proposal.start_date.strftime(settings.date_format),
                    end_date=proposal.end_date.strftime(settings.date_format),
                    exp_in_days=days_until_expire,
                    perc=usage_perc,
                    usage=self._build_usage_str(),
                    investment=self._build_investment_str()
                ).send_to(
                    to=f'{self._account_name}{settings.user_email_suffix}',
                    ffrom=settings.from_address,
                    subject=subject)

            session.commit()

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

    @classmethod
    def notify_unlocked(cls) -> None:
        """Lock any expired accounts"""

        for account in cls.find_unlocked():
            cls(account).notify_account()

    def renew(self, reset_usage=True) -> None:
        """Archive any expired investments and rollover unused service units"""

        with Session() as session:

            # Archive any investments which are past their end date
            investments_to_archive = session.query(Investor).filter(Investor.end_date <= date.today()).all()
            for investor_row in investments_to_archive:
                session.add(investor_row.to_archive_object())
                session.delete(investor_row)

            # Get total used and allocated service units
            current_proposal = self._get_proposal(session)
            total_proposal_sus = sum(getattr(current_proposal, c) for c in settings.clusters)
            total_usage = self._slurm_acct.get_total_usage()

            # Calculate number of investment SUs to roll over after applying SUs from the primary proposal
            archived_inv_sus = sum(inv.current_sus for inv in investments_to_archive)
            effective_usage = max(0, total_usage - total_proposal_sus)
            available_for_rollover = max(0, archived_inv_sus - effective_usage)
            to_rollover = int(available_for_rollover * settings.inv_rollover_fraction)

            # Add rollover service units to whatever the next available investment
            # If the conditional false then there are no more investments and the
            # service units that would have been rolled over are lost
            next_investment = self._get_investment(session)[0]
            if next_investment:
                next_investment.rollover_sus += to_rollover

            # Create a new user proposal and archive the old one
            new_proposal = Proposal(
                account_name=current_proposal.account_name,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                percent_notified=0
            )
            for cluster in settings.clusters:
                setattr(new_proposal, cluster, getattr(current_proposal, cluster))

            session.add(new_proposal)
            arx = current_proposal.to_archive_object()
            session.add(arx)
            session.delete(current_proposal)

            session.commit()

        # Set RawUsage to zero and unlock the account
        if reset_usage:
            self._slurm_acct.reset_raw_usage()
            self._slurm_acct.set_locked_state(False)
