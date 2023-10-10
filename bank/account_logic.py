"""The ``account_services`` module acts as the primary data access layer for the parent
application and defines the bulk of the account management logic.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date, datetime
from logging import getLogger
from math import ceil
from typing import Collection, Iterable, Optional, Union
from warnings import warn

from dateutil.relativedelta import relativedelta
from prettytable import PrettyTable
from sqlalchemy import delete, and_, not_, select

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

        account = SlurmAccount(account_name)
        self._account_name = account.account_name
        AccountServices.setup_db_account_entry(self._account_name)

    def _get_active_proposal_id(self) -> int:
        """Return the active proposal ID for the current account. If there are multiple "active" proposals,
        return the ID of the proposal with the most recent start date

        Raises:
            MissingProposalError: If no active proposal is found
        """

        subquery = select(Account.id).where(Account.name == self._account_name)

        active_proposal_id_query = select(Proposal.id) \
            .where(Proposal.account_id.in_(subquery)) \
            .where(Proposal.is_active) \
            .order_by(Proposal.start_date.desc())

        with DBConnection.session() as session:
            proposal_id = session.execute(active_proposal_id_query).scalars().first()

        if proposal_id is None:
            raise MissingProposalError(f'Account `{self._account_name}` has no active proposal.')

        return proposal_id

    def _verify_proposal_id(self, proposal_id: int) -> None:
        """Raise an error if a given ID does not belong to the current account

        Args:
            proposal_id: The ID of a proposal

        Raises:
            MissingProposalError: If the proposal ID does not match the current account
        """

        query = select(Proposal) \
            .join(Account) \
            .where(Account.name == self._account_name)\
            .where(Proposal.id == proposal_id)

        with DBConnection.session() as session:
            if session.execute(query).scalars().first() is None:
                raise MissingProposalError(f'Account `{self._account_name}` has no proposal with ID {proposal_id}.')

    @staticmethod
    def _verify_cluster_values(**clusters_sus: int) -> None:
        """Raise an error if given cluster names or service units are invalid

        Args:
            **clusters_sus: Service units for each cluster
        Raises:
            ValueError: If a cluster name is not defined in settings
            ValueError: If service units are negative
        """

        for cluster, sus in clusters_sus.items():
            if cluster not in settings.clusters and cluster != "all_clusters":
                raise ValueError(f'{cluster} is not a valid cluster name.')

            if sus < 0:
                raise ValueError('Service units cannot be negative.')

    def create(
            self,
            start: Optional[date] = date.today(),
            end: Optional[date] = None,
            force: Optional[bool] = False,
            **clusters_sus: int
    ) -> None:
        """Create a new proposal for the account

        Args:
            start: The start date of the proposal, default is today
            end: Date of the proposal expiration, default is 1 year
            force: Optionally replace current active proposal with provided values, default is false
            **clusters_sus: Service units to allocate to each cluster
        """

        end = end or (start + relativedelta(years=1))

        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()

        with DBConnection.session() as session:
            # Make sure new proposal does not overlap with existing proposals
            overlapping_proposal_sub_1 = select(Account.id) \
                                     .where(Account.name == self._account_name)
            overlapping_proposal_query = select(Proposal) \
                    .where(Proposal.account_id.in_(overlapping_proposal_sub_1)) \
                    .where(
                           and_(
                               not_(and_(start < Proposal.start_date, end <= Proposal.start_date)),
                               not_(and_(start >= Proposal.end_date, end > Proposal.end_date))
                          )
                    )
            overlapping_proposal = session.execute(overlapping_proposal_query).scalars().first()
            if overlapping_proposal:
                if force:
                    warn("Creating the proposal despite overlap with an existing proposal")
                else:
                    raise ProposalExistsError(f'By default, proposals for a given account cannot overlap: \n'
                                              f'    existing range {overlapping_proposal.start_date} '
                                              f'- {overlapping_proposal.end_date} \n'
                                              f'    provided range {start} - {end} \n'
                                              f'This can be overridden with the `--force` flag')

            # Create the new proposal and allocations
            new_proposal = Proposal(
                percent_notified=0,
                start_date=start,
                end_date=end,
                allocations=[
                    Allocation(cluster_name=cluster, service_units_total=sus) for cluster, sus in clusters_sus.items()
                ]
            )

            # Assign the proposal to user account
            account_query = select(Account).where(Account.name == self._account_name)
            account = session.execute(account_query).scalars().first()
            account.proposals.append(new_proposal)

            session.add(account)
            session.commit()

            LOG.info(f"Created proposal {new_proposal.id} for {self._account_name}")

    def delete(self, proposal_id: int = None) -> None:
        """Delete a proposal from the current account

        Args:
            proposal_id: ID of the proposal to delete

        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        self._verify_proposal_id(proposal_id)

        with DBConnection.session() as session:
            session.execute(delete(Proposal).where(Proposal.id == proposal_id))
            session.execute(delete(Allocation).where(Allocation.proposal_id == proposal_id))
            session.commit()

            LOG.info(f"Deleted proposal {proposal_id} for {self._account_name}")

    def modify_date(
            self,
            proposal_id: Optional[int] = None,
            start: Optional[date] = None,
            end: Optional[date] = None,
            force: Optional[bool] = False
    ) -> None:
        """Overwrite the date of an account proposal

        Args:
            proposal_id: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            start: Optionally set a new start date for the proposal
            end: Optionally set a new end date for the proposal
            force: Optionally overwrite dates even if it would cause overlap with another proposal
        Raises:
            MissingProposalError: If the proposal ID does not match the account
            ValueError: If neither a start date nor end date are provided, and if provided start/end dates are not in
            chronological order with amongst themselves or with the existing DB values.
            ProposalExistsError: If the proposal being created would otherwise overlap with an existing proposal,
            and the force flag is not provided.
        """

        proposal_id = proposal_id or self._get_active_proposal_id()
        self._verify_proposal_id(proposal_id)

        with DBConnection.session() as session:
            # Get default proposal values
            query = select(Proposal).where(Proposal.id == proposal_id)
            proposal = session.execute(query).scalars().first()
            start = start or proposal.start_date
            end = end or proposal.end_date

            if start >= end:
                raise ValueError(f'Start and end dates need to be in proper chronological order: {start} >= {end}. '
                                 f'If providing start or end alone, this comparison is between the provided date and '
                                 f'the proposals\'s existing value')

            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()

            # Find any overlapping proposals (not including the proposal being modified)
            overlapping_proposal_sub_1 = select(Account.id) \
                                     .where(Account.name == self._account_name)
            overlapping_proposal_query = select(Proposal) \
                    .where(Proposal.account_id.in_(overlapping_proposal_sub_1)) \
                    .where(
                            and_(
                               not_(and_(start < Proposal.start_date, end <= Proposal.start_date)),
                               not_(and_(start >= Proposal.end_date, end > Proposal.end_date))
                            )
                          )
            overlapping_proposal = session.execute(overlapping_proposal_query).scalars().first()
            if overlapping_proposal:
                if force:
                    warn("Modifying the proposal dates despite overlap with an existing proposal")
                else:
                    raise ProposalExistsError(f'By default, proposals for a given account cannot overlap: \n'
                                              f'    existing range {overlapping_proposal.start_date} '
                                              f'- {overlapping_proposal.end_date} \n'
                                              f'    provided range {start} - {end} \n'
                                              f'This can be overridden with the `--force` flag')

            # Update the proposal record
            if start != proposal.start_date:
                proposal.start_date = start
                LOG.info(f"Overwriting start date on investment {proposal.id} for account {self._account_name}")

            if end != proposal.end_date:
                proposal.end_date = end
                LOG.info(f"Overwriting end date on investment {proposal.id} for account {self._account_name}")

            session.commit()

            LOG.info(f"Modified proposal {proposal.id} for account {self._account_name}.")

    def add_sus(self, proposal_id: Optional[int] = None, **clusters_sus: int) -> None:
        """Add service units to an account proposal

        Args:
            proposal_id: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            **clusters_sus: Service units to add for each cluster
        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        proposal_id = proposal_id or self._get_active_proposal_id()
        self._verify_proposal_id(proposal_id)
        self._verify_cluster_values(**clusters_sus)

        query = select(Proposal).where(Proposal.id == proposal_id)
        with DBConnection.session() as session:
            proposal = session.execute(query).scalars().first()

            # Make sure allocation is present for provided cluster names
            for cluster in clusters_sus.keys():
                if cluster not in [alloc.cluster_name for alloc in proposal.allocations]:
                    proposal.allocations.append(Allocation(cluster_name=cluster,
                                                           service_units_total=0,
                                                           service_units_used=0,))

            # Update each allocation with the values to be added
            for allocation in proposal.allocations:
                allocation.service_units_total += clusters_sus.get(allocation.cluster_name, 0)

            session.commit()

            LOG.info(f"Modified proposal {proposal_id} for account {self._account_name}. Added {clusters_sus}")

    def subtract_sus(self, proposal_id: Optional[int] = None, **clusters_sus: int) -> None:
        """Subtract service units from an account proposal

        Args:
            proposal_id: Modify a specific proposal by its inv_id (Defaults to currently active proposal)
            **clusters_sus: Service units to add for each cluster
        Raises:
            MissingProposalError: If the proposal ID does not match the account
        """

        proposal_id = proposal_id or self._get_active_proposal_id()
        self._verify_proposal_id(proposal_id)
        self._verify_cluster_values(**clusters_sus)

        query = select(Proposal).where(Proposal.id == proposal_id)
        with DBConnection.session() as session:
            proposal = session.execute(query).scalars().first()

            for allocation in proposal.allocations:
                allocation.service_units_total -= clusters_sus.get(allocation.cluster_name, 0)

            session.commit()

            LOG.info(f"Modified proposal {proposal_id} for account {self._account_name}. Removed {clusters_sus}")


class InvestmentServices:
    """Administrative tool for managing account Investments"""

    def __init__(self, account_name: str) -> None:
        """Create or administrate investment data for the given Slurm account
        Args:
            account_name: The name of the Slurm account to administrate

        Raises:
            MissingProposalError: If the account does not have an associated proposal
        """

        account = SlurmAccount(account_name)
        self._account_name = account.account_name
        AccountServices.setup_db_account_entry(self._account_name)

        with DBConnection.session() as session:
            # Check if the Account has an associated proposal
            proposal_query = select(Proposal).join(Account).where(Account.name == account_name)
            proposal = session.execute(proposal_query).scalars().first()
            if proposal is None:
                raise MissingProposalError(f'Account {account_name} does not hav an associated proposal')

    def _get_active_investment_id(self) -> int:
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

        query = select(Investment) \
            .join(Account) \
            .where(Account.name == self._account_name) \
            .where(Investment.id == inv_id)

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

        if int(sus) <= 0:
            raise ValueError('Service units must be greater than zero.')

    def create(
            self,
            sus: int = 0,
            start: Optional[date] = date.today(),
            end: Optional[date] = None,
            num_inv: int = 1) -> None:
        """Add a new investment or series of investments to the given account

        Args:
            sus: The total number of service units to be added to the investment, or split equally across multiple
            investments with ``num_inv``
            start: The start date of the investment, or first in the sequence of investments, defaulting to today
            end: The expiration date of the investment, or first in the sequence of investments,
            defaulting to 12 months from ``start``
            num_inv: Divide ``sus`` equally across a number of sequential investments

        Raises:
            ValueError: If the SUs provided are less than 0, if the start date is later than the end date, or if the
            number of investments is less than 1.
        """

        # Validate arguments
        self._verify_service_units(sus)

        end = end or (start + relativedelta(years=1))
        if start >= end:
            raise ValueError(f'Argument start: {start} must be an earlier date than than end: {end}')

        if num_inv < 1:
            raise ValueError(f'Argument num_inv: {num_inv} must be >= 1')

        # Calculate number of service units per each investment
        duration = relativedelta(end, start)
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

                LOG.debug(f"Inserting investment {new_investment.id} for {self._account_name} with {sus} SUs")

                session.commit()

                LOG.info(f"Invested {sus} service units for account {self._account_name}")

    def delete(self, inv_id: int) -> None:
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

            LOG.info(f"Deleted investment {inv_id} for {self._account_name}")

    def modify_date(
            self,
            inv_id: Optional[int] = None,
            start: Optional[date] = None,
            end: Optional[date] = None) -> None:
        """Overwrite the start or end date of a given investment

        Args:
            inv_id: The ID of the investment to change, default is the active investment ID
            start: Optionally set a new start date for the investment
            end: Optionally set a new end date for the investment

        Raises:
            MissingInvestmentError: If the account does not have an investment
            ValueError: If neither a start date nor end date are provided, and if provided start/end dates are not in
            chronological order with amongst themselves or with the existing DB values.
        """

        inv_id = inv_id or self._get_active_investment_id()

        self._verify_investment_id(inv_id)

        query = select(Investment).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            investment = session.execute(query).scalars().first()
            start = start or investment.start_date
            end = end or investment.end_date

            # Validate provided start/end against DB entries
            if start >= end:
                raise ValueError(
                    f'Start and end dates need to be in proper chronological order: {start} >= {end}. If providing '
                    'start or end alone, this comparison is between the provided date and the investment\'s existing '
                    'value')

            # Make provided changes
            if start != investment.start_date:
                investment.start_date = start
                LOG.info(f"Overwriting start date on investment {investment.id} for account {self._account_name}")

            if end != investment.end_date:
                investment.end_date = end
                LOG.info(f"Overwriting end date on investment {investment.id} for account {self._account_name}")

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

        inv_id = inv_id or self._get_active_investment_id()
        self._verify_investment_id(inv_id)

        query = select(Investment).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            investment = session.execute(query).scalars().first()
            investment.service_units += sus
            investment.current_sus += sus

            session.commit()

            LOG.info(f"Added {sus} service units to investment {investment.id} for account {self._account_name}")

    def subtract_sus(self, inv_id: Optional[int], sus: int) -> None:
        """Subtract service units from the given investment

        Args:
            inv_id: The ID of the investment to change, default is the active investment ID
            sus: Number of service units to remove

        Raises:
            MissingInvestmentError: If the account does not have a proposal
        """

        self._verify_service_units(sus)

        inv_id = inv_id or self._get_active_investment_id()
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

            LOG.info(f'Removed {sus} service units to investment {investment.id} for account {self._account_name}')

    def advance(self, inv_id: Optional[int], sus: int) -> None:
        """Withdraw service units from future investments

        Args:
            inv_id: the investment ID to perform the advance on, default is the first active investment found
            sus: The number of service units to withdraw
        """

        self._verify_service_units(sus)
        inv_id = inv_id or self._get_active_investment_id()
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
                .where(Investment.is_expired is not False) \
                .where(Investment.id != active_investment.id)

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

                LOG.info(f'Withdrawing {to_withdraw} service units from investment {investment.id}')

                investment.current_sus -= to_withdraw
                investment.withdrawn_sus += to_withdraw
                active_investment.current_sus += to_withdraw

                # Check if we have withdrawn the requested number of service units
                sus -= to_withdraw
                if sus <= 0:
                    break

            session.commit()

            LOG.info(f"Advanced {(requested_withdrawal - sus)} service units for account {self._account_name}")


class AccountServices:
    """Administrative tool for managing individual bank accounts"""

    def __init__(self, account_name: str) -> None:
        """Administrate user data at the account level

        Args:
            account_name: The name of the account to administrate
        """

        account = SlurmAccount(account_name)
        self._account_name = account.account_name
        self.setup_db_account_entry(self._account_name)

        subquery = select(Account.id).where(Account.name == self._account_name)

        self._active_proposal_query = select(Proposal) \
            .where(Proposal.account_id.in_(subquery)) \
            .where(Proposal.is_active) \
            .order_by(Proposal.start_date.desc())

        self._recent_proposals_query = select(Proposal) \
            .where(Proposal.account_id.in_(subquery))

        self._active_investment_query = select(Investment) \
            .where(Investment.account_id.in_(subquery)) \
            .where(Investment.is_active) \
            .order_by(Investment.start_date.desc())

        self._investments_query = select(Investment) \
            .where(Investment.account_id.in_(subquery))

    @staticmethod
    def _calculate_percentage(usage: int, total: int) -> int:
        """Calculate the percentage ``100 * usage / total`` and return 0 if the answer is infinity"""

        if total > 0:
            return 100 * usage // total

        return 0

    def _get_active_proposal_end_date(self) -> str:
        """Return the end date for the Account's active proposal"""

        with DBConnection.session() as session:
            proposal = session.execute(self._active_proposal_query).scalars().first()

            if not proposal:
                raise MissingProposalError('Account has no active proposal')

            return proposal.end_date

    def _get_active_proposal_allocation_info(self) -> Collection[Allocation]:
        """Return the allocations associated with the Account's active proposal"""

        with DBConnection.session() as session:
            proposal = session.execute(self._active_proposal_query).scalars().first()

            if not proposal:
                raise MissingProposalError('Account has no active proposal')

            return proposal.allocations

    def _build_usage_table(self) -> PrettyTable:
        """Return a human-readable summary of the account usage and allocation"""

        slurm_acct = SlurmAccount(self._account_name)
        output_table = PrettyTable(header=False, padding_width=5)

        with DBConnection.session() as session:
            proposal = session.execute(self._active_proposal_query).scalars().first()
            investments = session.execute(self._active_investment_query).scalars().all()

            if not proposal:
                recent_proposal = session.execute(self._recent_proposals_query).scalars().first()
                if not recent_proposal:
                    raise MissingProposalError('This account has never had a proposal')
                recent_proposal_end = recent_proposal.end_date.strftime(settings.date_format)
                recent_proposal_alloc_status = (
                [f'{alloc.cluster_name}:{alloc.service_units_used}/{alloc.service_units_total}' for alloc in
                recent_proposal.allocations])
                raise MissingProposalError('\nMost recent proposal end date:\n'
                                           f'    {recent_proposal_end}\n'
                                           'Most recent proposal allocation status:\n'
                                           f'    {recent_proposal_alloc_status}')

            # Proposal End Date as first row
            output_table.title = f"{self._account_name} Proposal Information"
            output_table.add_row(['Proposal End Date:', proposal.end_date.strftime(settings.date_format), ""],
                                 divider=True)

            output_table.add_row(['Proposal ID:', proposal.id, ""], divider=True)
            output_table.add_row(["", "", ""], divider=True)

            aggregate_usage_total = 0
            allocation_total = 0
            floating_su_usage = 0
            floating_su_total = 0
            floating_su_remaining = 0

            for allocation in proposal.allocations:

                # Skip any cluster that does not have service units awarded on it
                if not allocation.service_units_total:
                    continue

                cluster_name = str.upper(allocation.cluster_name)

                # Determine whether there is a floating allocation
                if allocation.cluster_name == 'all_clusters':
                    floating_su_usage = allocation.service_units_used
                    floating_su_total = allocation.service_units_total
                    floating_su_remaining = floating_su_total - floating_su_usage
                    continue

                # Gather usage data from sreport
                usage_data = slurm_acct.get_cluster_usage_per_user(cluster=allocation.cluster_name,
                                                                   start=proposal.start_date,
                                                                   end=proposal.end_date,
                                                                   in_hours=True)

                

                # Skip displaying usage data if there is none, just show cluster total
                if not usage_data:
                    output_table.add_row([f"Cluster: {cluster_name}",
                                          f"Total SUs: {allocation.service_units_total}",""], divider=True)
                    output_table.add_row(["", "", ""], divider=True)
                    continue

                total_usage_on_cluster = sum(usage_data.values())
                total_cluster_percent = self._calculate_percentage(total_usage_on_cluster,
                                                                   allocation.service_units_total)
                output_table.add_row([f"Cluster: {cluster_name}",
                                     f"Total SUs: {allocation.service_units_total}",""], divider=True)

                # Build a list of individual user usage on the current cluster
                output_table.add_row(["User", "SUs Used", "% Used"], divider=True)
                for index, data in enumerate(usage_data.items()):
                    user = data[0]
                    user_usage = data[1]
                    user_percentage = self._calculate_percentage(user_usage, allocation.service_units_total) or "N/A"
                    if index != len(usage_data.items()) - 1:
                        output_table.add_row([user, user_usage, user_percentage])
                    else:
                        # Last user is a divider
                        output_table.add_row([user, user_usage, user_percentage], divider=True)

                # Overall usage
                output_table.add_row([f'Overall for {cluster_name}', total_usage_on_cluster, total_cluster_percent],
                                     divider=True)
                output_table.add_row(["", "", ""], divider=True)

                aggregate_usage_total += total_usage_on_cluster
                allocation_total += allocation.service_units_total

            usage_percentage = self._calculate_percentage(aggregate_usage_total, allocation_total)

            floating_su_percent = self._calculate_percentage(floating_su_usage, floating_su_total)
            output_table.add_row(['Floating SUs', "SUs Remaining", "% Used"], divider=True)
            output_table.add_row([f'*Floating SUs', "", ""])
            output_table.add_row([f'are applied on', "", ""])
            output_table.add_row([f'any cluster to', str(floating_su_remaining)+'*', floating_su_percent])
            output_table.add_row([f'cover usage above', "", ""])
            output_table.add_row([f'Total SUs', "", ""], divider=True)

            # Add another inner table describing aggregate usage
            if not investments:
                output_table.add_row(['Aggregate Usage', usage_percentage, ""], divider=True)
            else:
                investment_total = sum(inv.service_units for inv in investments)
                investment_remaining =  sum(inv.current_sus for inv in investments)
                investment_used = investment_total - investment_remaining
                investment_percentage = self._calculate_percentage(investment_used, investment_total)

                output_table.add_row(['Investment SUs', "SUs Remaining", "% Used"], divider=True)
                output_table.add_row([f'**Investment SUs', "",""])
                output_table.add_row([f'are applied on', "", ""])
                output_table.add_row([f'any cluster to', str(investment_remaining)+"**", investment_percentage])
                output_table.add_row([f'cover usage above',"",""])
                output_table.add_row([f'Total SUs', "", ""], divider=True)
                output_table.add_row(['Aggregate Usage', usage_percentage, ""])
                output_table.add_row(['(no investments)', "", ""])

            return output_table

    def _build_investment_table(self) -> PrettyTable:
        """Return a human-readable summary of the account's investments

        The returned string is empty if there are no investments
        """

        with DBConnection.session() as session:
            investments = session.execute(self._investments_query).scalars().all()
            if not investments:
                raise MissingInvestmentError('Account has no investments')

            table = PrettyTable(header=False, padding_width=5, max_width=80)
            table.title =f"{self._account_name} Investment Information"

            for inv in investments: 
                table.add_row(['Investment ID','Start Date','End Date'], divider=True)
                table.add_row([inv.id, inv.start_date.strftime(settings.date_format), inv.end_date.strftime(settings.date_format)], divider=True)

                table.add_row(['Total Service Units', 'Current SUs', 'Withdrawn SUs'], divider=True)
                table.add_row([inv.service_units, inv.current_sus, inv.withdrawn_sus], divider=True)
                table.add_row(['','',''], divider=True)
        return table

    def info(self) -> None:
        """Print a summary of service units allocated to and used by the account"""

        try:
            print(self._build_usage_table())
            print("\n")

        except MissingProposalError as e:
            print(f'Account {self._account_name} has no active proposal: {str(e)}')

        try:
            print(self._build_investment_table())

        except MissingInvestmentError:
            pass

    @staticmethod
    def setup_db_account_entry(account_name) -> Account:
        """Insert an entry into the database for a new SLURM account if it does not already exist"""

        with DBConnection.session() as session:
            # Check if the Account has an entry in the database
            account_query = select(Account).where(Account.name == account_name)
            account = session.execute(account_query).scalars().first()

            # If not, insert the new account so proposals/investments can reference it
            if account is None:
                account = Account(name=account_name)
                session.add(account)
                session.commit()
                LOG.info(f"Created DB entry for account {account_name}")

    def notify(self) -> None:
        """Send any pending usage alerts to the account"""

        proposal_query = select(Proposal).join(Account) \
            .where(Account.name == self._account_name) \
            .where(Proposal.is_active)

        with DBConnection.session() as session:
            for proposal in session.execute(proposal_query).scalars().all():
                self._notify_proposal(proposal)

    def _notify_proposal(self, proposal):
        # Determine the next usage percentage that an email is scheduled to be sent out
        slurm_acct = SlurmAccount(self._account_name)
        usage = slurm_acct.get_cluster_usage_total(start=proposal.start_date,
                                                   end=proposal.end_date)
        total_allocated = sum(alloc.service_units_total for alloc in proposal.allocations)
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

    def update_status(self) -> None:
        """Update the Bank database entries for an unlocked account given the usage values from SLURM,
        and lock the account if necessary

        Update the current usage for each allocation in the proposal from the values in SLURM's job accounting database.

        Using these values, determine which clusters the account is exceeding usage limits on, and determine if that
        usage can be covered by floating/investment service units, locking on the cluster if not.

        """

        # Update status runs daily
        end_date = date.today()
        start_date = end_date - relativedelta(days=1)

        slurm_acct = SlurmAccount(self._account_name)

        # Initialize usage to SUs used over the last day
        total_usage_exceeding_limits = slurm_acct.get_cluster_usage_total(start=start_date, end=end_date, in_hours=True)

        with DBConnection.session() as session:

            proposal = None
            investments = None
            floating_alloc = None

            # Default to locking on all clusters
            lock_clusters = Slurm.cluster_names()

            # Gather the account's active proposal and investments if they exist
            proposal = session.execute(self._active_proposal_query).scalars().first()
            investments = session.execute(self._active_investment_query).scalars().all()

        # Update proposal usage to reflect sreport output
            if proposal:
                total_usage_exceeding_limits = 0
                lock_clusters = []

                # Update within-cluster usage, building a list of clusters to potentially lock on
                for alloc in proposal.allocations:
                    if alloc.cluster_name == 'all_clusters':
                        floating_alloc = alloc
                        continue
                    else:
                        alloc.service_units_used += slurm_acct.get_cluster_usage_total(cluster=alloc.cluster_name,
                                                                                       start=start_date,
                                                                                       end=end_date,
                                                                                       in_hours=True)

                        sus_remaining = alloc.service_units_total - alloc.service_units_used

                        if sus_remaining <= 0:
                            total_usage_exceeding_limits -= sus_remaining
                            alloc.service_units_used = alloc.service_units_total
                            lock_clusters.append(alloc.cluster_name)

            if total_usage_exceeding_limits > 0:
                # Gather sources of surplus SUs
                sources = []
                if floating_alloc:
                    sources.append(floating_alloc)
                if investments:
                    for investment in investments:
                        sources.append(investment)

                for source in sources:
                    # Apply Floating Allocation
                    if type(source) == Allocation:
                        floating_sus = source.service_units_total - source.service_units_used
                        floating_sus_remaining = floating_sus - total_usage_exceeding_limits

                        # Floating SUs can cover usage
                        if floating_sus_remaining >= 0:
                            # Do not lock on any cluster, update floating SUs used
                            lock_clusters = []
                            source.service_units_used += total_usage_exceeding_limits
                            total_usage_exceeding_limits = 0
                            LOG.debug(f"Using floating SUs to cover usage for {self._account_name} on {lock_clusters}")
                            break

                        # Floating SUs can not cover usage
                        else:
                            # Exhaust floating SUs and continue to next source
                            total_usage_exceeding_limits -= floating_sus
                            floating_alloc.service_units_used = floating_alloc.service_units_total
                            continue

                    # Apply Investment SUs
                    else:

                        # Check if the investment is expired, continue on to the next one if so
                        if source.is_expired:
                            continue

                        investment_sus_remaining = source.current_sus - total_usage_exceeding_limits
                        # Investment can not cover
                        if investment_sus_remaining < 0:
                            total_usage_exceeding_limits -= source.current_sus
                            source.current_sus = 0
                            continue

                        else:
                            source.current_sus -= total_usage_exceeding_limits
                            lock_clusters = []
                            total_usage_exceeding_limits = 0
                            LOG.debug(f"Using investment SUs to cover usage for {self._account_name} on {lock_clusters}")
                            break

                # Lock if surplus SU sources could not cover usage exceeding proposal limits
                if total_usage_exceeding_limits > 0:
                    LOG.info(f"Locked {self._account_name} on {lock_clusters} due to insufficient floating "
                             f"or investment SUs to cover usage")
                    self.lock(clusters=lock_clusters)

            session.commit()

    def _set_account_lock(
            self,
            lock_state: bool,
            clusters: Optional[Collection[str]] = None,
            all_clusters: bool = False
    ) -> None:
        """Update the lock/unlocked states for the current account, only lock account if it has no purchased partitions
        within a cluster

        Args:
            lock_state: The new account lock state
            clusters: Name of the clusters to lock the account on. Defaults to all clusters.
            all_clusters: Lock the user on all clusters
        """

        if all_clusters:
            clusters = Slurm.cluster_names()

        for cluster in clusters:
            locked = lock_state

            try:
                # Determine whether a purchased partition exists on the cluster
                # using CRC's naming convention: partition name always
                # contains name of the account, e.g. eschneider-mpi
                for partition in Slurm.partition_names(cluster):
                    if partition.find(self._account_name) >= 0:
                        locked = False
                        LOG.info(
                            f"{self._account_name} is not locked on {cluster} because it has an investment partition")
                        break

                SlurmAccount(self._account_name).set_locked_state(locked, cluster)
            except CmdError:
                # Continue if SLURM cluster is unreachable by sinfo
                continue

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

        # Query database for all account names
        with DBConnection.session() as session:
            account_names = session.execute(select(Account.name)).scalars().all()

        # Build a generator for account names that match the lock state
        for account in account_names:
            try:
                if SlurmAccount(account).get_locked_state(cluster) == status:
                    yield account
            except AccountNotFoundError:
                continue

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
    def find_unlocked_account_names(cls) -> dict:
        """Provide a list of accounts that are unlocked on the clusters defined in SLURM

        Returns: A dictionary with cluster name as the keys and a generator yielding account names as the value
        """

        unlocked_accounts_by_cluster = {}
        numclusters = len(Slurm.cluster_names())
        cluster_progress = 0
        for cluster in Slurm.cluster_names():
            cluster_progress += 1
            LOG.info(f"Gathering unlocked accounts on {cluster}")
            unlocked_accounts_by_cluster[cluster] = set(cls._iter_accounts_by_lock_state(False, cluster))
            LOG.info(f"Gathered unlocked accounts progress {cluster_progress}/{numclusters}")

        return unlocked_accounts_by_cluster

    @classmethod
    def update_account_status(cls) -> None:
        """Update account usage information and lock any expired or overdrawn accounts"""

        # Log start of update status
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        LOG.info(f"STARTING Update_status {now}")

        # Gather all account names that are currently unlocked on some cluster
        LOG.info(f"Gathering unlocked accounts...")
        unlocked_accounts_by_cluster = cls.find_unlocked_account_names()

        # Build set of account names that are unlocked on any cluster
        account_names = set()
        for name_set in unlocked_accounts_by_cluster.values():
            account_names = account_names.union(name_set)

        # Set up progress indicator for log
        num_accounts = len(account_names)
        progress = 0

        # Update the status of any unlocked account
        for name in account_names:
            progress += 1
            #TODO: maintain this whitelist in settings?
            if name in ["root", "clcgenomics"]:
                continue
            try:
                LOG.info(f"Updating status for {name}...")
                account = AccountServices(name)
                account.update_status()
            except AccountNotFoundError:
                LOG.info(f"SLURM Account does not exist for {name}")
                continue

            LOG.info(f"Update status: {progress}/{num_accounts} updated")

        # Log end of update status
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        LOG.info(f"FINISHED Update_status {now}")

