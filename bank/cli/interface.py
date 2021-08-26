"""Functions used to support the application command line interface"""

import csv
import json
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
