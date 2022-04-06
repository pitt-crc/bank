"""The ``account_services`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import List, Union, Tuple, Optional

from . import settings
from .data_access import AccountDBAccess
from .exceptions import *
from .orm import Investment, Proposal, ProposalEnum, Allocation
from .system import SlurmAccount

Numeric = Union[int, float, complex]
LOG = getLogger('bank.account_services')


class ProposalServices:
    """Account logic for primary account proposals"""

    def __init__(self, account_name) -> None:
        self.account_name = account_name

    def create_proposal(
            self,
            type: ProposalEnum = ProposalEnum.Proposal,
            start: date = date.today(),
            duration: int = 365,
            **kwargs: int
    ) -> None:
        """Create a new proposal for the given account

        Args:
            type: The type of the proposal
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to add on to each cluster
        """

        with AccountDBAccess(self.account_name) as session:
            # Check for any overlapping proposals
            end_date = start + timedelta(days=duration)
            if session.get_overlapping_proposals(session, start, end_date):
                raise ProposalExistsError(f'Proposal already exists for account: {self.account_name}')

            # Create the new proposal and allocations
            new_proposal = Proposal(
                account_name=self.account_name,
                proposal_type=type,
                percent_notified=0,
                start_date=start,
                end_date=end_date,
                allocations=[
                    Allocation(cluster_name=cluster, service_units=sus) for cluster, sus in kwargs.items()
                ]
            )

            # Assign the proposal to user account
            account = session.get_account()
            account.proposals.append(new_proposal)

            session.add(account)
            session.commit()

        LOG.info(f"Created proposal {new_proposal.id} for {self.account_name}")

    def delete_proposal(self, pid: Optional[int] = None) -> None:
        """Delete the account's current proposal"""

        with AccountDBAccess(self.account_name) as session:
            proposal = session.get_proposal(pid=pid)
            session.execute(Proposal.delete().where(Proposal.id == proposal.id))
            session.commit()

        LOG.info(f"Deleted proposal {proposal.id} for {self.account_name}")

    def modify_proposal(
            self,
            pid: Optional[int] = None,
            type: ProposalEnum = ProposalEnum.Proposal,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            **kwargs: Union[int, date]
    ) -> None:
        """Replace the number of service units allocated to a given cluster

        Args:
            type: Optionally change the type of the proposal
            start_date: Optionally set a new start date for the proposal
            end_date: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        # Build a query for finding the proposal needing deletion

        with AccountDBAccess(self.account_name) as session:
            proposal = session.get_proposal(session, pid=pid)
            proposal.proposal_type = type or proposal.proposal_type
            proposal.start_date = start_date or proposal.start_date
            proposal.end_date = end_date or proposal.end_date

            for allocation in proposal.allocations:
                allocation.service_units = kwargs.get(allocation.cluster_name, allocation.service_units)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self.account_name}. Overwrote {kwargs}")

    def add_sus(self, pid: Optional[int] = None, **kwargs: int) -> None:
        """Add service units to the account's current allocation

        Args:
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with AccountDBAccess(self.account_name) as session:
            proposal = session.get_proposal(session, pid=pid)
            for allocation in proposal.allocations:
                allocation.service_units += kwargs.get(allocation.cluster_name, 0)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self.account_name}. Added {kwargs}")

    def subtract_sus(self, pid: Optional[int] = None, **kwargs: int) -> None:
        """Subtract service units from the account's current allocation

        Args:
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        with AccountDBAccess(self.account_name) as session:
            proposal = session.get_proposal(session, pid=pid)
            for allocation in proposal.allocations:
                allocation.service_units -= kwargs.get(allocation.cluster_name, 0)

            session.commit()

        LOG.info(f"Modified proposal {proposal.id} for account {self.account_name}. Removed {kwargs}")


class InvestmentServices(AccountDBAccess):
    """Data access for investment information associated with a given account"""

    def __init__(self, account_name: str) -> None:
        """An existing account in the bank

        Args:
            account_name: The name of the account
        """

        super().__init__(account_name)

        # Raise an error if there is no active user proposal
        with AccountDBAccess(self.account_name) as session:
            proposal = self.get_proposal(session)

        if proposal.proposal_type is not ProposalEnum.Proposal:
            raise ValueError('Investments cannot be added/managed for class accounts')

    def create_investment(self, sus: int, start: date = date.today(), duration: int = 365, num_inv: int = 1) -> None:
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

        with AccountDBAccess(self.account_name) as session:
            self.get_proposal(session)

            for i in range(num_inv):
                start_this = start + i * duration
                end_this = start + (i + 1) * duration

                new_investor = Investment(
                    account_name=self.account_name,
                    start_date=start_this,
                    end_date=end_this,
                    service_units=sus_per_instance,
                    current_sus=sus_per_instance,
                    withdrawn_sus=0,
                    rollover_sus=0
                )

                session.add(new_investor)
                LOG.debug(f"Inserting investment {new_investor.id} for {self.account_name} with allocation of `{sus}`")

            session.commit()

        LOG.info(f"Invested {sus} service units for account {self.account_name}")

    def delete_investment(self, id: int) -> None:
        """Delete one of the account's associated investments

        Args:
            id: The id of the investment to delete
        """

        with AccountDBAccess(self.account_name) as session:
            investment = self._get_investment(session, id)
            session.add(investment.to_archive_object())
            session.query(Investment).filter(Investment.id == investment.id).delete()
            session.commit()

        LOG.info(f'Archived investment {investment.id} for account {self.account_name}')

    def add(self, id: int, sus: int) -> None:
        """Add service units to the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to add

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        with AccountDBAccess(self.account_name) as session:
            investment = self._get_investment(session, id)
            investment.service_units += sus
            investment.current_sus += sus
            session.commit()

        LOG.info(f'Added {sus} service units to investment {investment.id} for account {self.account_name}')

    def subtract(self, id: int, sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            id: The id of the investment to change
            sus: Number of service units to remove

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        with AccountDBAccess(self.account_name) as session:
            investment = self._get_investment(session, id)
            if investment.current_sus < sus:
                raise ValueError(f'Cannot subtract {sus}. Investment {id} only has {investment.current_sus} available.')

            investment.service_units -= sus
            investment.current_sus -= sus
            session.commit()

        LOG.info(f'Removed {sus} service units to investment {investment.id} for account {self.account_name}')

    def overwrite(self, id: int, sus: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> None:
        """Overwrite service units allocated to the given investment

        Args:
            id: The id of the investment to change
            sus: New number of service units to assign to the investment
            start_date: Optionally set a new start date for the investment
            end_date: Optionally set a new end date for the investment

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        with AccountDBAccess(self.account_name) as session:
            investment = self._get_investment(session, id)

            if sus is not None:
                investment.service_units = sus

            if start_date:
                investment.start_date = start_date

            if end_date:
                investment.end_date = end_date

            session.commit()

        LOG.info(f'Overwrote service units on investment {investment.id} to {sus} for account {self.account_name}')

    def advance(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        requested_withdrawal = sus

        with AccountDBAccess(self.account_name) as session:
            # Query all of the account's investments from the database and sort them
            # so that younger investments (i.e., with later start dates) come first
            investments = session.query(Investment) \
                .filter(Investment.account_name == self.account_name) \
                .order_by(Investment.start_date.desc()) \
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

        LOG.info(f'Advanced {requested_withdrawal - sus} service units for account {self.account_name}')


class AdminServices(AccountDBAccess):
    """Administration for existing bank accounts"""

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def _build_usage_str(self) -> str:
        """Return a human-readable summary of the account ussage and allocation"""

        with AccountDBAccess(self.account_name) as session:
            proposal = self.get_proposal(session)
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
        with AccountDBAccess(self.account_name) as session:
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

        with AccountDBAccess(self.account_name) as session:
            proposal = self.get_proposal(session)

            # Determine the next usage percentage that an email is scheduled to be sent out
            usage = self._slurm_acct.get_total_usage()
            allocated = proposal.total_allocated
            usage_perc = min(int(usage / allocated * 100), 100)
            next_notify_perc = next((perc for perc in sorted(settings.notify_levels) if perc >= usage_perc), 100)

            email = None
            days_until_expire = (proposal.end_date - date.today()).days
            if days_until_expire == 0:
                email = settings.expired_proposal_notice
                subject = f'The account for {self.account_name} has reached its end date'
                self._slurm_acct.set_locked_state(True)

            elif days_until_expire in settings.warning_days:
                email = settings.expiration_warning
                subject = f'Your proposal expiry reminder for account: {self.account_name}'

            elif proposal.percent_notified < next_notify_perc <= usage_perc:
                proposal.percent_notified = next_notify_perc
                email = settings.usage_warning
                subject = f"Your account {self.account_name} has exceeded a proposal threshold"

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
                    to=f'{self.account_name}{settings.user_email_suffix}',
                    ffrom=settings.from_address,
                    subject=subject)

            session.commit()

    @staticmethod
    def find_unlocked() -> Tuple[str]:
        """Return the names for all unexpired proposals with unlocked accounts

        Returns:
            A tuple of account names
        """

        # Query database for accounts that are unlocked and is_expired
        with AccountDBAccess(self.account_name) as session:
            proposals: List[Proposal] = session.query(Proposal).filter((Proposal.end_date < date.today())).all()
            return tuple(p.account_name for p in proposals if not SlurmAccount(p.account_name).get_locked_state())

    @classmethod
    def notify_unlocked(cls) -> None:
        """Lock any is_expired accounts"""

        for account in cls.find_unlocked():
            cls(account).notify_account()

    def renew(self, reset_usage: bool = True) -> None:
        """Archive any is_expired investments and rollover unused service units"""

        with AccountDBAccess(self.account_name) as session:

            # Archive any investments which are past their end date
            investments_to_archive = session.query(Investment).filter(Investment.end_date <= date.today()).all()
            for investor_row in investments_to_archive:
                session.add(investor_row.to_archive_object())
                session.delete(investor_row)

            # Get total used and allocated service units
            current_proposal = self.get_proposal(session)
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
                proposal_type=current_proposal.proposal_type,
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
