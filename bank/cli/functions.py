from datetime import date
from logging import getLogger

from bank.orm import Account, Proposal, Session
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


def lock_with_notification(account: str) -> None:
    """Lock the given user account

    Args:
        account: The name of the account to lock
    """

    LOG.info(f'Locking account `{account}`')

    # Construct a shell command using the ``sacctmgr`` command line tool
    clusters = ','.join(app_settings.clusters)
    cmd = f'sacctmgr -i modify account where account={account} cluster={clusters} set GrpTresRunMins=cpu=0'
    ShellCmd(cmd).raise_err()

    with Session() as session:
        account = session.query(Account).filter(account_name=account).first()
        account.notify(app_settings.proposal_expires_notification)


def release_hold(account: str) -> None:
    """Unlock the given user account

    Args:
        account: The name of the account  to unlock
    """

    with Session() as session:
        account = session.query(Account).filter(account_name=account).first()
        account.set_locked_state(locked=False, notify=False)


def usage(account: str) -> None:
    """Print account usage as comma seperated values

    Args:
        account: The name of the account  to print information for
    """

    with Session() as session:
        account = session.query(Account).filter(account_name=account).first()

    print(','.join(('type', *app_settings.clusters)))
    print('proposal:', account.proposal.row_to_csv(app_settings.clusters))
    for inv in account.investments:
        print(f'investment ({inv.id}):', inv.row_to_csv(app_settings.clusters))


def find_unlocked() -> None:
    """Print the names for all unexpired proposals with unlocked accounts"""

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
