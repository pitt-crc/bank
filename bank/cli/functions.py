from datetime import date, timedelta
from logging import getLogger
from math import ceil

import numpy as np

from bank.orm import Account, Investor, Proposal, Session
from bank.orm.enum import ProposalType
from bank.settings import app_settings
from bank.system import SlurmAccount

LOG = getLogger('bank.cli')


def info(account: str) -> None:
    """Print proposal information for the given account

    Args:
        account: The name of the account to print information for
    """

    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account).first()
        account.raise_missing_proposal()

        # Print all database entries associate with the account as an ascii table
        print(account.proposal.row_to_ascii_table())
        for inv in account.investments:
            print(inv.row_to_ascii_table())


def usage(account: str) -> None:
    """Print a summary of service units used by the given account

    Args:
        account: The name of the account  to print information for
    """

    # Get account information from the database
    with Session() as session:
        acc = session.query(Account).filter(Account.account_name == account).first()

        # Print the table header
        print(f"|{'-' * 82}|")
        print(f"|{'Proposal End Date':^30}|{acc.proposal.end_date.strftime(app_settings.date_format) :^51}|")

        # Print usage information for the primary proposal
        usage_total = 0
        slurm = SlurmAccount(account)
        for cluster in app_settings.clusters:
            cluster_usage = slurm.raw_cluster_usage(cluster, in_hours=True)
            cluster_allocation = getattr(acc.proposal, cluster)
            overall_usage = np.round(100 * cluster_usage / cluster_allocation, 2) or 'N/A'
            usage_total += cluster_usage
            print(f"|{'-' * 82}|\n"
                  f"|{'Cluster: ' + cluster + ', Available SUs: ' + cluster_allocation :^82}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n"
                  f"|{'Overall':^20}|{cluster_usage:^30d}|{overall_usage:^30}|\n"
                  f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|")

        # Print usage information concerning investments
        print(f"|{'Aggregate':^82}|")
        print("|{'-' * 40:^40}|{'-' * 41:^41}|")
        if acc.investment_total == 0:
            print(f"|{'Aggregate Usage':^40}|{100 * usage_total / acc.allocation_total:^41.2f}|")
            print(f"|{'-' * 82}|")

        else:
            print(f"|{'Investments Total':^40}|{str(acc.investment_total) + '^a':^41}|\n"
                  f"|{'Aggregate Usage (no investments)':^40}|{100 * usage_total / acc.allocation_total:^41.2f}|\n"
                  f"|{'Aggregate Usage':^40}|{100 * usage_total / (acc.allocation_total + acc.investment_total):^41.2f}|\n"
                  f"|{'-' * 40:^40}|{'-' * 41:^41}|\n"
                  f"|{'^a Investment SUs can be used across any cluster':^82}|\n"
                  f"|{'-' * 82}|")


def reset_raw_usage(account: str):
    """Print account usage as comma seperated values

    Args:
        account: The name of the account  to print information for
    """

    LOG.info(f'Resetting raw usage for account `{account}`')
    SlurmAccount(account).reset_raw_usage()


def find_unlocked() -> None:
    """Print the names for all unexpired proposals with unlocked accounts"""

    # Query database for accounts that are unlocked and expired
    with Session() as session:
        proposals = session.query(Proposal).filter_by(
            (Proposal.end_date < date.today()) and (not Proposal.account.locked_state)
        ).all()

    for proposal in proposals:
        print(proposal.account.account_name)


def set_account_lock(account: str, lock_state: bool, notify: bool) -> None:
    """Unlock the given user account

    Args:
        account: The name of the account  to unlock
    """

    account = SlurmAccount(account)
    account.set_locked_state(lock_state)
    if notify:
        account.notify(app_settings.proposal_expires_notification)


def alert_account(account: str) -> None:
    members = app_settings.notify_levels
    exceeded = [usage > x.to_percentage() for x in members]

    try:
        index = exceeded.index(False)
        result = 0 if index == 0 else members[index - 1]

    except ValueError:
        result = 100

    return result


def insert(account_name: str, prop_type: str, **sus_per_cluster: int) -> None:
    """Create a new proposal for the given account

    Args:
        account_name: The account name to add a proposal for
        prop_type: The type of proposal
        **sus_per_cluster: Service units to add on to each cluster
    """

    proposal_type = ProposalType.from_string(prop_type)
    proposal_duration = timedelta(days=365)
    start_date = date.today()
    new_proposal = Proposal(
        proposal_type=proposal_type.value,
        percent_notified=0,
        start_date=start_date,
        end_date=start_date + proposal_duration,
        **sus_per_cluster
    )

    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account_name)
        account.proposal = new_proposal
        session.commit()

    sus_as_str = ', '.join(f'{k}={v}' for k, v in sus_per_cluster.items())
    LOG.info(f"Inserted proposal with type {proposal_type.name} for {account_name} with {sus_as_str}")


def add(account_name, **sus_per_cluster: int) -> None:
    """Add service units for the given account / clusters

    Args:
        account_name: The account name to add a proposal for
        **sus_per_cluster: Service units to add on to each cluster
    """

    LOG.debug(f"Adding sus to {account_name}: {sus_per_cluster}")
    with Session() as session:
        proposal = session.query(Account).filter_by(Account.account_name == account_name).proposal
        for cluster, su in sus_per_cluster.items():
            setattr(proposal, cluster, getattr(proposal, cluster) + su)

        session.commit()

        su_string = ', '.join(f'{getattr(proposal, k)} on {k}' for k in app_settings.clusters)
        LOG.info(f"Added SUs to proposal for {account_name}, new limits are {su_string}")


def modify(account_name, **kwargs) -> None:
    """Replace the currently allocated service units for an account with new values

    Args:
        account_name: The account name to add a proposal for
        **kwargs: New values to set in the proposal
    """

    LOG.debug(f"Modifying proposal for {account_name}: {kwargs}")
    with Session() as session:
        proposal = session.query(Account).filter_by(Account.account_name == account_name)
        for cluster, su in kwargs.items():
            setattr(proposal, cluster, su)

        session.commit()

        su_string = ', '.join(f'{getattr(proposal, k)} on {k}' for k in app_settings.clusters)
        LOG.info(f"Changed proposal for {account_name} to {su_string}")


def investor(account_name, sus: int) -> None:
    """Add a new investor proposal for the given account

    Args:
        account_name: The account name to add a proposal for
        sus: The number of service units to add
    """

    # Investor accounts last 5 years
    start_date = date.today()
    end_date = start_date + timedelta(days=5 * 365)

    # Service units should be a valid number
    new_investor = Investor(
        proposal_type=ProposalType.Investor,
        start_date=start_date,
        end_date=end_date,
        service_units=sus,
        current_sus=ceil(sus / 5),
        withdrawn_sus=0,
        rollover_sus=0
    )

    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account_name)
        account.investments.append(new_investor)
        session.commit()

    LOG.info(f"Inserted investment for {account_name} with per year allocations of `{sus}`")


def investor_modify(inv_id: int, sus: int) -> None:
    raise NotImplementedError()


def renewal(account_name, **sus) -> None:
    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account_name).first()

        # Move the old account proposal to the archive table
        session.add(account.proposal.to_archive_object())
        account.proposal.delete()

        # Move any expired investments to the archive table
        for investment in account.investments:
            if investment.expired:
                session.add(investment.to_archive_obj())
                investment.delete()

        # Add new proposal and rollover investment service units
        account.proposal = Proposal(**sus)
        account.rollover_investments()
        session.commit()

    # Set RawUsage to zero and unlock the account
    slurm_acct = SlurmAccount(account_name)
    slurm_acct.reset_raw_usage()
    slurm_acct.set_locked_state(False)


def withdraw(acount: str, sus: int) -> None:
    raise NotImplementedError()
