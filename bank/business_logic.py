"""The ``account_services`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from typing import List, Union, Tuple, Optional

from . import settings
from .dao import ProposalData, InvestmentData
from .exceptions import *
from .orm import Investment, Proposal, Session, ProposalEnum
from .system import SlurmAccount

Numeric = Union[int, float]
LOG = getLogger('bank.account_services')


class ProposalServices:
    """Account logic for primary account proposals"""

    def __init__(self, account_name: str) -> None:
        """Administrate proposal data for the given user account

        Args:
            account_name: The name of the account to administrate
        """

        self._account_name = account_name
        self._pdata = ProposalData(account_name)

    def _default_pid(self, pid: Union[None, int]) -> int:
        """Return the default proposal ID to administrate

        If ``pid`` is ``None``, return the ID of the currently active proposal.
        Otherwise, return ``pid``.

        Args:
            pid: Either ``None`` or a proposal ID

        Raises:
            MissingProposalError: If ``pid`` is ``None`` and the account has no active proposal
        """

        if pid is not None:
            return pid

        proposal_df = self._pdata.get_current_proposal_data()
        if proposal_df.empty:
            raise MissingProposalError(f'Could not find active proposal for account {self._account_name}')

        return proposal_df.id[0]

    def create_proposal(
            self,
            type: ProposalEnum = ProposalEnum.Proposal,
            start: date = date.today(),
            duration: int = 365,
            **kwargs: int
    ) -> None:
        """Create a new proposal for the account

        Args:
            type: The type of the proposal
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to allocate to each cluster
        """

        end = start + timedelta(days=duration)
        if self._pdata.get_proposal_data_in_range(start, end):
            raise ProposalExistsError('Proposals for a given account cannot overlap.')

        self._pdata.create_proposal(type=type, start=start, duration=duration, **kwargs)

    def delete_proposal(self, pid: Optional[int] = None):
        """Delete a proposal from the current account

        Args:
            pid: ID of the proposal to delete
        """

        self._pdata.delete_proposal(self._default_pid(pid))

    def modify_proposal(
            self,
            pid: Optional[int] = None,
            type: ProposalEnum = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            **kwargs: Union[int, date]
    ) -> None:
        """Overwrite the properties of the account's current allocation

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            type: Optionally change the type of the proposal
            start_date: Optionally set a new start date for the proposal
            end_date: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        # Find any overlapping proposals minus the proposal being modified
        pid = self._default_pid(pid)
        overlapping_proposals = self._pdata.get_proposal_data_in_range(start_date, end_date)
        conflicting_proposal_ids = set(overlapping_proposals.pid) - {pid}

        # Prevent modified proposal from creating an overlap with other proposals
        if conflicting_proposal_ids:
            raise ProposalExistsError('Proposals for a given account cannot overlap.')

        self._pdata.modify_proposal(self._default_pid(pid), type, start_date, end_date, **kwargs)

    def add_sus(self, pid: Optional[int] = None, **kwargs) -> None:
        """Add service units to the account's current allocation

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        self._pdata.add_sus(self._default_pid(pid), **kwargs)

    def subtract_sus(self, pid: Optional[int] = None, **kwargs) -> None:
        """Subtract service units from the account's current allocation

        Args:
            pid: Modify a specific proposal by its id (defaults to currently active proposal)
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the account does not have a proposal
        """

        self._pdata.subtract_sus(self._default_pid(pid), **kwargs)


class InvestmentServices(InvestmentData):
    """Data access for investment information associated with a given account"""

    def __init__(self, account_name):
        super().__init__(account_name)

        # Raise an error if there is no active user proposal
        with Session() as session:
            if self.get_proposal(session).proposal_type is not ProposalEnum.Proposal:
                raise ValueError('Investments cannot be added/managed for class accounts')

    def advance(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        requested_withdrawal = sus

        with Session() as session:
            # Query all of the account's investments from the database and sort them
            # so that younger investments (i.e., with later start dates) come first
            investments = self.get_all_investments(session, expired=False)
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


class AdminServices:
    """Administration for existing bank accounts"""

    def __init__(self, accout_name):
        self.account_name = accout_name
        self._slurm_acct = SlurmAccount(accout_name)

    @staticmethod
    def _calculate_percentage(usage: Numeric, total: Numeric) -> Numeric:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage / total

        return 0

    def _build_usage_str(self) -> str:
        """Return a human-readable summary of the account usage and allocation"""

        with Session() as session:
            proposal = self.get_proposal(session)
            try:
                investments = session.get_investment()

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
                investments = self.get_all_investments(session, expired=True)

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
        with Session() as session:
            proposals: List[Proposal] = session.query(Proposal).filter((Proposal.end_date < date.today())).all()
            return tuple(p.account_name for p in proposals if not SlurmAccount(p.account_name).get_locked_state())

    @classmethod
    def notify_unlocked(cls) -> None:
        """Lock any is_expired accounts"""

        for account in cls.find_unlocked():
            cls(account).notify_account()

    def renew(self, reset_usage: bool = True) -> None:
        """Archive any is_expired investments and rollover unused service units"""

        with Session() as session:

            # Archive any investments which are past their end date
            investments_to_archive = session.query(Investment).filter(Investment.end_date <= date.today()).all()
            for investor_row in investments_to_archive:
                session.add(investor_row.to_archive_object())
                session.delete(investor_row)

            # Get total used and allocated service units
            current_proposal = session.get_proposal
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
            next_investment = self.get_investment(session)
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
