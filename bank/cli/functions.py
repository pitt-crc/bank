from datetime import date, timedelta
from logging import getLogger
from math import ceil

from bank.orm import Account, Investor, Proposal, Session
from bank.orm.enum import ProposalType
from bank.settings import app_settings
from bank.utils import ShellCmd

LOG = getLogger('bank.cli')


def info(account: str) -> None:
    """Print proposal information for the given account

    Args:
        account: The name of the account to print information for
    """

    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account).first()
        account.require_proposal()

        # Print all database entries associate with the account as an ascii table
        print(account.proposal.row_to_ascii_table())
        for inv in account.investments:
            print(inv.row_to_ascii_table())


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


def add(account_name, **sus_per_cluster: int) -> None:
    """Add service units for the given account / clusters

    Args:
        account_name: The account name to add a proposal for
        **sus_per_cluster: Service units to add on to each cluster
    """

    # Update row in database
    with Session() as session:
        account = session.query(Account).filter_by(Account.account_name == account_name)
        for cluster, su in sus_per_cluster.items():
            setattr(account.proposal, cluster, getattr(account.proposal, cluster) + su)

        session.commit()

        su_string = ', '.join(f'{getattr(account.proposal, k)} on {k}' for k in app_settings.clusters)
        LOG.info(f"Added SUs to proposal for {account_name}, new limits are {su_string}")


def change(account_name, **sus_per_cluster: int) -> None:
    """Replace the currently allocated service units for an account with new values

    Args:
        account_name: The account name to add a proposal for
        **sus_per_cluster: New service unit allocation on to each cluster
    """

    # Update row in database
    with Session() as session:
        account = session.query(Account).filter_by(Account.account_name == account_name)
        for cluster, su in sus_per_cluster.items():
            setattr(account.proposal, cluster, su)

        session.commit()

        su_string = ', '.join(f'{getattr(account.proposal, k)} on {k}' for k in app_settings.clusters)
        LOG.info(f"Changed proposal for {account_name} with {su_string}")


def get_sus(account: str) -> None:
    """Print proposal information for the given account

    Args:
        account: The name of the account to print information for
    """

    with Session() as session:
        account = session.query(Account).filter(Account.account_name == account).first()
        account.require_proposal()

        # Print all database entries associate with the account in csv format
        print('Proposal:', account.proposal.row_to_csv(app_settings.clusters))
        for inv in account.investments:
            print(f'Investment {inv.id}:', inv.row_to_csv(app_settings.clusters))


def set_account_lock(account: str, lock_state: bool, notify: bool) -> None:
    """Unlock the given user account

    Args:
        account: The name of the account  to unlock
    """

    lock_state_int = 0 if lock_state else -1
    clusters = ','.join(app_settings.clusters)

    # Construct a shell command using the ``sacctmgr`` command line tool
    cmd = f'sacctmgr -i modify account where account={account} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'
    ShellCmd(cmd).raise_err()

    if notify:
        with Session() as session:
            account = session.query(Account).filter(account_name=account).first()
            account.notify(app_settings.proposal_expires_notification)


def usage(account: str) -> None:
    """Print account usage as comma seperated values

    Args:
        account: The name of the account  to print information for
    """

    # Get proposal data from the database
    with Session() as session:
        account_row = session.query(Account).filter(Account.account_name == account).first()

    print(','.join(('type', *app_settings.clusters)))
    print('proposal:', account_row.proposal.row_to_csv(app_settings.clusters))
    for inv in account_row.investments:
        print(f'investment ({inv.id}):', inv.row_to_csv(app_settings.clusters))


def find_unlocked() -> None:
    """Print the names for all unexpired proposals with unlocked accounts"""

    # Query database for accounts that are unlocked and expired
    with Session() as session:
        proposals = session.query(Proposal).filter_by(
            (Proposal.end_date < date.today()) and (not Proposal.account.locked_state)
        ).all()

    for proposal in proposals:
        print(proposal.account.account_name)


def reset_raw_usage(account: str):
    """Print account usage as comma seperated values

    Args:
        account: The name of the account  to print information for
    """

    LOG.info(f'Resetting raw usage for account `{account}`')
    clusters = ','.join(app_settings.clusters)
    ShellCmd(f'sacctmgr -i modify account where account={account} cluster={clusters} set RawUsage=0')
