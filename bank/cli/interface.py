"""Functions used to support the application command line interface"""

import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

from ..dao import Account
from ..orm import Proposal, Session
from ..settings import app_settings


def alloc_sus(path: Path) -> None:
    """Export allocated service units to a CSV file

    Args:
        path: The path to write exported data to
    """

    with Session() as session:
        proposals = session.query(Proposal).all()

    columns = ('account', *app_settings.clusters)
    with path.open('w', newline='') as ofile:
        writer = csv.writer(ofile)
        writer.writerow(columns)
        for proposal in proposals:
            writer.writerow(proposal[col] for col in columns)


def find_unlocked() -> None:
    """Print the names for all unexpired proposals with unlocked accounts"""

    today = date.today()
    for proposal in Session().query(Proposal).all():
        is_locked = Account(proposal.account).get_locked_state()
        is_expired = proposal.end_date >= today
        if not (is_locked or is_expired):
            print(proposal.account)


def get_sus(account: Account) -> None:
    """Print the current service units for the given account in CSV format

    Args:
        account: The account to inspect
    """

    proposal, investments = account.get_proposals()
    proposal_sus = (proposal[c] for c in app_settings.clusters)
    investor_sus = [['investment', inv.current_sus + inv.rollover_sus] for inv in investments]

    writer = csv.writer(sys.stdout, lineterminator=os.linesep)
    writer.writerow(['type', *app_settings.clusters])
    writer.writerow(['proposal', *proposal_sus])
    writer.writerows(investor_sus)


def info(account: Account) -> None:
    """Print proposal information for the given account

    Args:
        account: The account to print information for
    """

    proposal, investments = account.get_proposals()
    if proposal:
        print('Proposal')
        print('---------------')
        print(json.dumps(proposal.to_json(), indent=2))
        print()

    for investor in investments:
        print(f'Investment: {investor.id:3}')
        print(f'---------------')
        print(json.dumps(investor.to_json(), indent=2))
        print()
