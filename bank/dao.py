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
            if not inv:
                raise MissingInvestmentError(f'Account {self.account_name} has no investment with id {id}')

        else:
            inv = session.query(Investor).filter(Investor.account_name == self._account_name).all()
            if not inv:
                raise MissingInvestmentError(f'Account {self.account_name} has no associated investments')

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

            if v <= 0:
                raise ValueError('Service unit values must be greater than zero')

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

        LOG.info(f"Deleted proposal {proposal.id} for {self._account_name}")

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

        LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Added {kwargs}")

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

        LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Removed {kwargs}")

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
            self._get_proposal_info(session)

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

    def create_investment(self, sus: int, start: date = date.today(), duration: int = 365, repeat=0) -> None:
        """Add a new investor proposal for the given account

        Args:
            sus: The number of service units to add
            start: The start date of the proposal
            duration: How many days before the investment expires
            repeat: Spread out the given service units equally across n additional investment instances
        """

        duration = timedelta(days=duration)
        sus_per_instance = ceil(sus / (repeat + 1))
        with Session() as session:
            self._get_proposal_info(session)

            for _ in range(repeat, repeat + 1):
                new_investor = Investor(
                    account_name=self._account_name,
                    start_date=start,
                    end_date=start + duration,
                    service_units=sus,
                    current_sus=sus_per_instance,
                    withdrawn_sus=0,
                    rollover_sus=0
                )

                session.add(new_investor)
                start += duration
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
            investment.service_units -= sus
            session.commit()

        LOG.info(f'Removed {sus} service units to investment {investment.id} for account {self._account_name}')

    def overwrite(self, id: int, sus: int) -> None:
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
            session.commit()

        LOG.info(f'Overwrote service units on investment {investment.id} to {sus} for account {self._account_name}')

    def advance(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        self._raise_invalid_sus(sus)
        with Session() as session:
            investments = session.query(Investor) \
                .filter(Investor.account_name == self._account_name) \
                .order_by(Investor.start_date) \
                .all()

            # Make sure there are enough service units in the account to withdraw
            available_sus = sum(inv.service_units - inv.withdrawn_sus for inv in investments)
            if sus > available_sus:
                raise ValueError(f"Requested to withdraw {sus} but the account only has {available_sus} SUs available.")

            # Go through investments in order of age and start withdrawing
            for investment in investments:
                maximum_withdrawal = investment.service_units - investment.withdrawn_sus
                to_withdraw = min(sus, maximum_withdrawal)
                investment.current_sus += to_withdraw
                investment.withdrawn_sus += to_withdraw

                LOG.info(f'Withdrawing {to_withdraw} service units from investment {investment.id}')

                # Determine if we are done processing investments
                sus -= to_withdraw
                if sus <= 0:
                    break

            session.commit()

        LOG.info(f'Advanced {sus} service units for account {self._account_name}')

    def renew(self) -> None:
        raise NotImplementedError()


class AdminServices(BaseDataAccess):
    """Administration for existing bank accounts"""

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def print_info(self) -> None:
        """Print a summary of service units allocated to and used by the account"""

        with Session() as session:
            proposal = self._get_proposal_info(session)
            investments = self._get_investment(session)

        # Print the table header
        print(f"|{'-' * 82}|")
        print(f"|{'Proposal End Date':^30}|{proposal.end_date.strftime(settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        allocation_total = 0
        for cluster in settings.clusters:
            usage = self._slurm_acct.get_cluster_usage(cluster, in_hours=True)
            allocation = getattr(proposal, cluster)
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
        investment_total = sum(inv.service_units for inv in investments)
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

        with Session() as session:
            proposal = self._get_proposal_info(session)

        # Determine the next usage percentage that an email is scheduled to be sent out
        usage = sum(self._slurm_acct.get_cluster_usage(c) for c in settings.clusters())
        allocated = sum(proposal[c] for c in settings.clusters)
        usage_perc = int(usage / allocated * 100)
        next_notify = settings.notify_levels[bisect_left(settings.notify_levels, usage_perc)]

        email = None
        end_date = proposal.end_date.strftime(settings.date_format)
        days_until_expire = (proposal.end_date - date.today()).days
        if days_until_expire in settings.warning_days:
            email = EmailTemplate(settings.expiration_warning)
            subject = f'Your proposal expiry reminder for account: {self._account_name}'

        elif days_until_expire == 0:
            email = EmailTemplate(settings.expired_proposal_notice)
            subject = f'The account for {self._account_name} was locked because it reached the end date {end_date}'

        elif proposal.percent_notified < next_notify <= usage_perc:
            with Session() as session:
                db_entry = session.query(Proposal).filter(Proposal.account_name == self._account_name).first()
                db_entry.percent_notified = next_notify
                session.commit()

            email = EmailTemplate(settings.usage_warning.format(perc=usage_perc))
            subject = f"Your account {self._account_name} has exceeded a proposal threshold"

        if email:
            formatted = email.format(
                account=self._account_name,
                start_date=proposal.start_date.strftime(settings.date_format),
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
