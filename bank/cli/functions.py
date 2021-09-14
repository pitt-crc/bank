from datetime import date, timedelta
from logging import getLogger

from bank.orm import Account, Proposal, Session
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
