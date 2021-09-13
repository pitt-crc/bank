import bank.cli.parser
from bank.cli.parser import date
from bank.dao import Account
from bank.orm import Proposal, Session
from bank.settings import app_settings


def info(account: Account) -> None:
    """Print proposal information for the given account

    Args:
        account: The account to print information for
    """

    # Print all database entries associate with the account as an ascii table
    print(account.proposal.row_to_ascii_table())
    for inv in account.investments:
        print(inv.row_to_ascii_table())


def lock_with_notification(account: Account) -> None:
    """Lock the given user account

    Args:
        account: The account to lock
    """

    account.set_locked_state(locked=True, notify=True)


def release_hold(account: Account) -> None:
    """Unlock the given user account

    Args:
        account: The account to unlock
    """

    account.set_locked_state(locked=False, notify=False)


def usage(account: Account) -> None:
    """Print account usage as comma seperated values

    Args:
        account: The account to print information for
    """

    print(','.join(('type', *app_settings.clusters)))
    print('proposal:', account.proposal.row_to_csv(app_settings.clusters))
    for inv in account.investments:
        print(f'investment ({inv.id}):', inv.row_to_csv(app_settings.clusters))


def find_unlocked() -> None:
    """Print the names for all unexpired proposals with unlocked accounts"""

    with Session() as session:
        proposals = session.query(Proposal).filter_by(Proposal.end_date < date.today()).all()

    for proposal in proposals:
        account = Account(proposal.account)
        if not account.locked_state:
            print(account.account_name)


