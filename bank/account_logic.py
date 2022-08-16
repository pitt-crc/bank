"""The ``account_services`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date, timedelta
from logging import getLogger
from math import ceil
from typing import Collection, Iterable, Optional, Union

from dateutil.relativedelta import relativedelta
from prettytable import PrettyTable
from sqlalchemy import between, delete, or_, select

from . import settings
from .exceptions import *
from .orm import Account, Allocation, DBConnection, Investment, Proposal
from .system import EmailTemplate, Slurm, SlurmAccount

Numeric = Union[int, float]
LOG = getLogger('bank.account_services')


class ProposalServices:
    """Administrative tool for managing account proposals"""

    def __init__(self, account_name: str) -> None:
        """Administrate proposal data for the given user account

        Args:
            account_name: The name of the account to administrate
        """

        self._account_name = account_name

    def _get_active_pid(self) -> None:
        """Return the active proposal ID for the current account

        Raises:
            MissingProposalError: If no active proposal is found
        """

        active_pid_query = select(Proposal.id) \
            .join(Account) \
            .where(Account.name == self._account_name) \
            .where(Proposal.is_active)

        with DBConnection.session() as session:
            pid = session.execute(active_pid_query).scalars().first()

        if pid is None:
            raise MissingProposalError(f'Account `{self._account_name}` has no active proposal.')

        return pid

    def _verify_proposal_id(self, pid: int) -> None:
        """Raise an error if a given ID does not belong to the current account

        Args:
            pid: The ID of a proposal

        Raises:
            MissingProposalError: If the proposal ID does not match the current account
        """

        query = select(Proposal).join(Account).where(Account.name == self._account_name).where(Proposal.id == pid)
        with DBConnection.session() as session:
            if session.execute(query).scalars().first() is None:
                raise MissingProposalError(f'Account `{self._account_name}` has no proposal with ID {pid}.')

    @staticmethod
    def _verify_cluster_values(**kwargs: int) -> None:
        """Raise an error if given cluster names or service units are invalid

        Args:
            **kwargs: Service units for each cluster

        Raises:
            ValueError: If a cluster name is not defined in settings
            ValueError: If service units are negative
        """

        for cluster, sus in kwargs.items():
            if cluster not in settings.clusters:
                raise ValueError(f'{cluster} is not a valid cluster name.')

            if sus < 0:
                raise ValueError('Service units cannot be negative.')

    def create_proposal(
            self,
            start: date = date.today(),
            duration: int = 12,
            **kwargs: int
    ) -> None:
        """Create a new proposal for the account

        Args:
            type: The type of the proposal
            start: The start date of the proposal
            duration: How many days before the proposal expires
            **kwargs: Service units to allocate to each cluster
        """

        with DBConnection.session() as session:
            # Make sure new proposal does not overlap with existing proposals
            expiration_date = start + relativedelta(months=12)
            last_active_day = expiration_date - timedelta(days=1)
            overlapping_proposal_query = select(Proposal).join(Account) \
                .where(Account.name == self._account_name) \
                .where(
                or_(
                    between(start, Proposal.start_date, Proposal.last_active_date),
                    between(last_active_day, Proposal.start_date, Proposal.last_active_date),
                    between(Proposal.start_date, start, last_active_day),
                    between(Proposal.last_active_date, start, last_active_day)
                )
            )

            if session.execute(overlapping_proposal_query).scalars().first():
                raise ProposalExistsError('Proposals for a given account cannot overlap.')

            # Create the new proposal and allocations
            new_proposal = Proposal(
                percent_notified=0,
                start_date=start,
                end_date=expiration_date,
                allocations=[
                    Allocation(cluster_name=cluster, service_units=sus) for cluster, sus in kwargs.items()
                ]
            )

            # Assign the proposal to user account
            account_query = select(Account).where(Account.name == self._account_name)
            account = session.execute(account_query).scalars().first()
            account.proposals.append(new_proposal)

            session.add(account)
            session.commit()
            LOG.info('Created proposal %d for %s', new_proposal.id, self._account_name)

    def delete_proposal(self, pid: Optional[int] = None) -> None:
        """Delete a proposal from the current account

        Args:
            pid: ID of the proposal to delete (Defaults to currently active proposal)

        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        pid = pid or self._get_active_pid()
        self._verify_proposal_id(pid)

        with DBConnection.session() as session:
            session.execute(delete(Proposal).where(Proposal.id == pid))
            session.execute(delete(Allocation).where(Allocation.proposal_id == pid))
            session.commit()
            LOG.info('Deleted proposal %d for %s', pid, self._account_name)

    def modify_proposal(
            self,
            pid: Optional[int] = None,
            start: Optional[date] = None,
            end: Optional[date] = None,
            **kwargs: Union[int, date]
    ) -> None:
        """Overwrite the properties of an account proposal

        Args:
            pid: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            type: Optionally change the type of the proposal
            start: Optionally set a new start date for the proposal
            end: Optionally set a new end date for the proposal
            **kwargs: New service unit values to assign for each cluster

        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        pid = pid or self._get_active_pid()
        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        with DBConnection.session() as session:
            # Get default proposal values
            query = select(Proposal).where(Proposal.id == pid)
            proposal = session.execute(query).scalars().first()
            start = start or proposal.start_date
            end = end or proposal.end_date
            if start >= end:
                raise ValueError('Proposal start date must be before the end date.')

            last_active_date = end - timedelta(days=1)

            # Find any overlapping proposals (not including the proposal being modified)
            overlapping_proposal_query = select(Proposal).join(Account) \
                .where(Account.name == self._account_name) \
                .where(Proposal.id != pid) \
                .where(
                or_(
                    between(start, Proposal.start_date, Proposal.last_active_date),
                    between(last_active_date, Proposal.start_date, Proposal.last_active_date),
                    between(Proposal.start_date, start, last_active_date),
                    between(Proposal.last_active_date, start, last_active_date)
                )
            )

            if session.execute(overlapping_proposal_query).scalars().first():
                raise ProposalExistsError('Proposals for a given account cannot overlap.')

            # Update the proposal record
            proposal.proposal_type = type
            proposal.start_date = start
            proposal.end_date = end
            for allocation in proposal.allocations:
                allocation.service_units = kwargs.get(allocation.cluster_name, allocation.service_units)

            session.commit()
            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}. Overwrote {kwargs}")

    def add_sus(self, pid: Optional[int] = None, **kwargs) -> None:
        """Add service units to an account proposal

        Args:
            pid: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            **kwargs: Service units to add for each cluster

        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        pid = pid or self._get_active_pid()
        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        query = select(Allocation).join(Proposal).where(Proposal.id == pid)
        with DBConnection.session() as session:
            allocations = session.execute(query).scalars().all()
            for allocation in allocations:
                allocation.service_units += kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {pid} for account {self._account_name}. Added {kwargs}")

    def subtract_sus(self, pid: Optional[int] = None, **kwargs) -> None:
        """Subtract service units from an account proposal

        Args:
            pid: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            **kwargs: Service units to subtract from each cluster

        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        pid = pid or self._get_active_pid()
        self._verify_proposal_id(pid)
        self._verify_cluster_values(**kwargs)

        query = select(Allocation).join(Proposal).where(Proposal.id == pid)
        with DBConnection.session() as session:
            allocations = session.execute(query).scalars().all()
            for allocation in allocations:
                allocation.service_units -= kwargs.get(allocation.cluster_name, 0)

            session.commit()
            LOG.info(f"Modified proposal {pid} for account {self._account_name}. Removed {kwargs}")


class InvestmentServices:
    """Administrative tool for managing account Investments"""

    def __init__(self, account_name: str) -> None:
        """Create or administrate investment data for the given Slurm account
        Args:
            account_name: The name of the Slurm account to administrate

        Raises:
            MissingProposalError: If the account does not have an associated proposal
            MissingInvestmentError: If the account does not have an active investment, and the operation being executed
            is not trying to create one.
        """

        self._account_name = account_name

        with DBConnection.session() as session:

            # Check if the Account has an associated proposal
            proposal_query = select(Proposal).join(Account).where(Account.name == account_name)
            proposal = session.execute(proposal_query).scalars().first()
            if proposal is None:
                raise MissingProposalError(f'Account {account_name} does not hav an associated proposal')

    def _get_active_investment_id(self) -> None:
        """Return the active investment ID for the current account

        Raises:
            MissingInvestmentError: If no active investment is found
        """

        with DBConnection.session() as session:

        # Determine the active investment ID
            active_inv_id_query = select(Investment.id) \
                .join(Account) \
                .where(Account.name == self._account_name) \
                .where(Investment.is_active)

            active_inv_id = session.execute(active_inv_id_query).scalars().first()
            if active_inv_id is None:
                raise MissingInvestmentError(f'Account `{self._account_name}` has no active investment.')
            return active_inv_id

    def _verify_investment_id(self, inv_id: int) -> None:
        """Raise an error if a given ID does not belong to the current account

        Args:
            inv_id: The ID of an investment

        Raises:
            MissingInvestmentError: If the investment ID does not match the current account
        """

        query = select(Investment).join(Account).where(Account.name == self._account_name).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            if session.execute(query).scalars().first() is None:
                raise MissingInvestmentError(f'Account `{self._account_name}` has no investment with ID {inv_id}.')

    @staticmethod
    def _verify_service_units(sus: int) -> None:
        """Raise an error if given service units are invalid

        Args:
            sus: Service units value to test

        Raises:
            ValueError: If service units are not positive
        """

        if sus <= 0:
            raise ValueError('Service units must be greater than zero.')

    def create_investment(
        self,
        sus: int,
        start: Optional[date] = date.today(),
        end: Optional[date] = start + relativedelta(months=12),
        num_inv: Optional[int] = 1) -> None:
        """Add a new investment or series of investments to the given account

        Args:
            sus: The total number of service units to be added to the investment, or split equally across multiple investments
            with ``num_inv``
            start: The start date of the investment, or first in the sequence of investments, defaulting to today
            end: The expiration date of the investment, or first in the sequence of investments, defaulting to 12 months
            from ``start``
            num_inv: Divide ``sus`` equally across a number of sequential investments

        Raises:
            ValueError: If the SUs provided are less than 0, if the start date is later than the end date, or if the
            number of investments is less than 1.
        """

        # Validate arguments
        self._verify_service_units(sus)

        if start < end:
            raise ValueError('Argument ``start`` must be an earlier date than than ``end``')

        if num_inv < 1:
            raise ValueError('Argument ``repeat`` must be >= 1')

        # Calculate number of service units per each investment
        duration = relativedelta(end,start)
        sus_per_instance = ceil(sus / num_inv)

        with DBConnection.session() as session:
            for i in range(num_inv):

                # Determine the start and end of the current disbursement
                start_this = start + (i * duration)
                end_this = start_this + duration

                new_investment = Investment(
                    start_date=start_this,
                    end_date=end_this,
                    service_units=sus_per_instance,
                    current_sus=sus_per_instance,
                    withdrawn_sus=0,
                    rollover_sus=0
                )

                account = session.execute(select(Account).where(Account.name == self._account_name)).scalars().first()
                account.investments.append(new_investment)
                session.add(account)
                LOG.debug(
                    'Inserting investment %d for %s with %d service units',
                    new_investment.id,
                    self._account_name,
                    sus)

                session.commit()

            LOG.info('Invested %d service units for account %s', sus, self._account_name)

    def delete_investment(self, inv_id: int) -> None:
        """Delete one of the account's associated investments

        Args:
            inv_id: The inv_id of the investment to delete

        Raises:
            MissingInvestmentError: If the given ID does not match the current account
        """

        # Validate Arguments
        self._verify_investment_id(inv_id)

        # Delete the investment with the provided ID
        with DBConnection.session() as session:
            session.execute(delete(Investment).where(Investment.id == inv_id))
            session.commit()
            LOG.info('Deleted investment %d for %s', inv_id, self._account_name)

    def modify_date(self, inv_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None) -> None:
        """Overwrite the start or end date of a given investment

        Args:
            inv_id: The ID of the investment to change, default is the active investment ID
            start: Optionally set a new start date for the investment
            end: Optionally set a new end date for the investment

        Raises:
            MissingInvestmentError: If the account does not have an investment
            ValueError: If neither a start date or end date are provided, and if provided start/end dates are not in
            chronological order with amongst themselves or with the existing DB values.
        """

        # Validate Arguments
        if not start or end:
            raise ValueError('``modify_date`` requires either a new ``start`` or new ``end`` date')
        if (start and end) and start > end:
            raise ValueError('``start`` needs to be a date before ``end``')

        inv_id = inv_id or self._get_active_inv_id()

        self._verify_investment_id(inv_id)

        query = select(Investment).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            investment = session.execute(query).scalars().first()

            # Validate provided start/end against DB entries
            if (start and not end) and start > investment.end_date:
                raise ValueError(
                    f'If providing ``start`` alone, it needs to be earlier than the current end date: {investment.end_date}')
            if (end and not start) and end < investment.start_date:
                raise ValueError(
                    f'If providing ``end`` alone, it needs to be later than the current start date: {investment.start_date}')

            # Make provided changes
            if start:
                investment.start_date = start
                LOG.info('Overwriting start date on investment %s for account %s', investment.id, self._account_name)
            if end:
                investment.end_date = end
                LOG.info('Overwriting end date on investment %s for account %s', investment.id, self._account_name)

            session.commit()

    def add_sus(self, inv_id: Optional[int], sus: int) -> None:
        """Add service units to the given investment

        Args:
            inv_id: The ID of the investment to change, default is the active investment ID
            sus: Number of service units to add

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._verify_service_units(sus)

        inv_id = inv_id or self._get_active_inv_id()
        self._verify_investment_id(inv_id)

        query = select(Investment).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            investment = session.execute(query).scalars().first()
            investment.service_units += sus
            investment.current_sus += sus

            session.commit()
            LOG.info(
                'Added %d service units to investment %d for account %s',
                sus,
                investment.id,
                self._account_name)

    def subtract_sus(self, inv_id: Optional[int], sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            inv_id: The ID of the investment to change, default is the active investment ID
            sus: Number of service units to remove

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._verify_service_units(sus)

        inv_id = inv_id or self._get_active_inv_id()
        self._verify_investment_id(inv_id)

        query = select(Investment).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            investment = session.execute(query).scalars().first()
            if investment.current_sus < sus:
                raise ValueError(
                    f'Cannot subtract {sus}. Investment {inv_id} only has {investment.current_sus} available.')

            investment.service_units -= sus
            investment.current_sus -= sus

            session.commit()
            LOG.info(
                'Removed %d service units from investment %d for account %s',
                sus,
                investment.id, self._account_name)

    def advance(self, sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            sus: The number of service units to withdraw
        """

        self._verify_service_units(sus)
        inv_id = self._get_active_inv_id()
        requested_withdrawal = sus

        with DBConnection.session() as session:
            # Find the investment to add service units into
            active_investment_query = select(Investment).where(Investment.id == inv_id)
            active_investment = session.execute(active_investment_query).scalars().first()
            if not active_investment:
                raise MissingInvestmentError(f'Account does not have a currently active investment to advance into.')

            # Find investments to take service units out of
            usable_investment_query = select(Investment).join(Account) \
                .where(Account.name == self._account_name) \
                .where(not Investment.is_expired == False) \
                .where(Investment.id != active_investment.id) \
                .order_by(Investment.start_date.desc())

            usable_investments = session.execute(usable_investment_query).scalars().all()
            if not usable_investments:
                raise MissingInvestmentError(f'Account has no investments to advance service units from.')

            # Make sure there are enough service units to cover the withdrawal
            available_sus = sum(inv.service_units - inv.withdrawn_sus for inv in usable_investments)
            if sus > available_sus:
                raise ValueError(
                    f"Requested to withdraw {sus} but the account only has {available_sus} SUs available.")

            # Move service units from future investments into the current investment
            for investment in usable_investments:
                maximum_withdrawal = investment.service_units - investment.withdrawn_sus
                to_withdraw = min(sus, maximum_withdrawal)

                LOG.info('Withdrawing %d service units from investment %d', to_withdraw, investment.id)
                investment.current_sus -= to_withdraw
                investment.withdrawn_sus += to_withdraw
                active_investment.current_sus += to_withdraw

                # Check if we have withdrawn the requested number of service units
                sus -= to_withdraw
                if sus <= 0:
                    break

            session.commit()

        LOG.info('Advanced %d service units for account %s', (requested_withdrawal - sus), self._account_name)


class AccountServices:
    """Administrative tool for managing individual bank accounts"""

    def __init__(self, account_name: str) -> None:
        """Administrate user data at the account level

        Args:
            account_name: The name of the account to administrate
        """

        self._account_name = account_name

        self._proposal_query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(Proposal.is_active)

        self._investment_query = select(Investment).join(Account) \
            .where(Account.name == self._account_name). \
            where(Investment.is_active)

    @staticmethod
    def _calculate_percentage(usage: int, total: int) -> int:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage // total

        return 0

    def _build_usage_table(self) -> PrettyTable:
        """Return a human-readable summary of the account usage and allocation"""

        slurm_acct = SlurmAccount(self._account_name)
        output_table = PrettyTable(header=False, padding_width=0)
        with DBConnection.session() as session:
            proposal = session.execute(self._proposal_query).scalars().first()
            investments = session.execute(self._investment_query).scalars().all()

            if not proposal:
                raise MissingProposalError('Account has no proposal')

            usage_total = 0
            allocation_total = 0
            for allocation in proposal.allocations:
                usage_data = slurm_acct.get_cluster_usage(allocation.cluster_name, in_hours=True)
                total_cluster_usage = sum(usage_data.values())
                total_cluster_percent = self._calculate_percentage(total_cluster_usage, allocation.service_units)

                # Build an inner table of individual user usage on the current cluster
                user_usage_table = PrettyTable(border=False, field_names=['User', 'SUs Used', 'Percentage of Total'])
                for user, user_usage in usage_data.items():
                    user_percentage = self._calculate_percentage(user_usage, allocation.service_units) or ''
                    user_usage_table.add_row([user, user_usage, user_percentage])

                # Add the table created above to the outer table that will eventually be returned
                output_table.add_row(f"Cluster: {allocation.cluster_name}, Available SUs: {allocation.service_units}")
                output_table.add_row(user_usage_table)
                output_table.add_row(['Overall', total_cluster_usage, total_cluster_percent])

                usage_total += total_cluster_usage
                allocation_total += allocation.service_units

            usage_percentage = self._calculate_percentage(usage_total, allocation_total)
            investment_total = sum(inv.service_units for inv in investments)
            investment_percentage = self._calculate_percentage(usage_total, allocation_total + investment_total)

            # Add another inner table describing aggregate usage
            output_table.add_row(['Aggregate'])
            aggregate_table = PrettyTable(border=False, header=False)
            if investment_total == 0:
                aggregate_table.add_row(['Aggregate Usage', usage_percentage])
                output_table.add_row(aggregate_table)

            else:
                aggregate_table.add_row(['Investments Total', str(investment_total) + '^a'])
                aggregate_table.add_row(['Aggregate Usage (no investments)', usage_percentage])
                aggregate_table.add_row(['Aggregate Usage', investment_percentage])
                output_table.add_row(aggregate_table)
                output_table.add_row('^a Investment SUs can be used across any cluster')

            return output_table

    def _build_investment_table(self) -> PrettyTable:
        """Return a human-readable summary of the account's investments

        The returned string is empty if there are no investments
        """

        with DBConnection.session() as session:
            investments = session.execute(self._investment_query).scalars().all()
            if not investments:
                raise MissingInvestmentError('Account has no investments')

            table = PrettyTable(
                fields=['Total Investment SUs', 'Start Date', 'Current SUs', 'Withdrawn SUs', 'Rollover SUs'])
            for inv in investments:
                table.add_row([
                    inv.service_units,
                    inv.start_date.strftime(settings.date_format),
                    inv.current_sus,
                    inv.withdrawn_sus,
                    inv.withdrawn_sus])

        return table

    def print_info(self) -> None:
        """Print a summary of service units allocated to and used by the account"""

        try:
            print(self._build_usage_table())
            print(self._build_investment_table())

        except MissingProposalError:
            print(f'Account {self._account_name} has no current proposal')

        except MissingInvestmentError:
            pass

    def notify(self) -> None:
        """Send any pending usage alerts to the account"""

        proposal_query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(Proposal.exhaustion_date is not None) \
            .where(Proposal.start_date < date.today())

        with DBConnection.session() as session:
            for proposal in session.execute(proposal_query).scalars().all():
                self._notify_proposal(proposal)

    def _notify_proposal(self, proposal):
        # Determine the next usage percentage that an email is scheduled to be sent out
        slurm_acct = SlurmAccount(self._account_name)
        usage = slurm_acct.get_total_usage()
        total_allocated = sum(alloc.service_units for alloc in proposal.allocations)
        usage_perc = min(int(usage / total_allocated * 100), 100)
        next_notify_perc = next((perc for perc in sorted(settings.notify_levels) if perc >= usage_perc), 100)

        email = None
        days_until_expire = (proposal.end_date - date.today()).days
        if days_until_expire <= 0:
            email = EmailTemplate(settings.expired_proposal_notice)
            subject = f'The account for {self._account_name} has reached its end date'

        elif days_until_expire in settings.warning_days:
            email = EmailTemplate(settings.expiration_warning)
            subject = f'Your proposal expiry reminder for account: {self._account_name}'

        elif proposal.percent_notified < next_notify_perc <= usage_perc:
            proposal.percent_notified = next_notify_perc
            email = EmailTemplate(settings.usage_warning)
            subject = f"Your account {self._account_name} has exceeded a proposal threshold"

        if email:
            email.format(
                account_name=self._account_name,
                start=proposal.start_date.strftime(settings.date_format),
                end=proposal.end_date.strftime(settings.date_format),
                exp_in_days=days_until_expire,
                perc=usage_perc,
                usage=self._build_usage_table(),
                investment=self._build_investment_table()
            ).send_to(
                to=f'{self._account_name}{settings.user_email_suffix}',
                ffrom=settings.from_address,
                subject=subject)

    def update_account_status(self) -> None:
        """Close any expired proposals/investments and lock the account if necessary"""

        raise NotImplementedError

    def _set_account_lock(
            self,
            lock_state: bool,
            clusters: Optional[Collection[str]] = None,
            all_clusters: bool = False
    ) -> None:
        """Update the lock/unlocked states for the current account

        Args:
            lock_state: The new account lock state
            clusters: Name of the clusters to lock the account on. Defaults to all clusters.
            all_clusters: Lock the user on all clusters
        """

        if all_clusters:
            clusters = Slurm.cluster_names()

        for cluster in clusters:
            SlurmAccount(self._account_name).set_locked_state(lock_state, cluster)

    def lock(self, clusters: Optional[Collection[str]] = None, all_clusters=False) -> None:
        """Lock the account on the given clusters

        Args:
            clusters: Name of the clusters to lock the account on. Defaults to all clusters.
            all_clusters: Lock the user on all clusters
        """

        self._set_account_lock(True, clusters, all_clusters)

    def unlock(self, clusters: Optional[Collection[str]] = None, all_clusters=False) -> None:
        """Unlock the account on the given clusters

        Args:
            clusters: Name of the clusters to unlock the account on. Defaults to all clusters.
            all_clusters: Lock the user on all clusters
        """

        self._set_account_lock(False, clusters, all_clusters)


class AdminServices:
    """Administrative tasks for managing the banking system as a whole"""

    @staticmethod
    def _iter_accounts_by_lock_state(status: bool, cluster: str) -> Iterable[str]:
        """Return a collection of account names matching the lock state on the given cluster

        Args:
            status: The lock state to check for
            cluster: The name of the cluster to check the lock state on

        Returns:
            A tuple of account names
        """

        # Query database for accounts that are unlocked and expired
        account_name_query = (select(Account.name).join(Proposal).where(Proposal.end_date < date.today()))
        with DBConnection.session() as session:
            account_names = session.execute(account_name_query).scalars().all()

        for account in account_names:
            if SlurmAccount(account).get_locked_state(cluster) == status:
                yield account

    @classmethod
    def list_locked_accounts(cls, cluster: str) -> None:
        """Print account names that are locked on a given cluster

        Args:
            cluster: The name of the cluster to check the lock state on
        """

        print(*cls._iter_accounts_by_lock_state(True, cluster), sep='\n')

    @classmethod
    def list_unlocked_accounts(cls, cluster: str) -> None:
        """Print account names that are unlocked on a given cluster

        Args:
            cluster: The name of the cluster to check the lock state on
        """

        print(*cls._iter_accounts_by_lock_state(False, cluster), sep='\n')

    @classmethod
    def update_account_status(cls) -> None:
        """Update account usage information and lock any expired or overdrawn accounts"""

        for account in cls.find_unlocked():
            account.update_account_status()
