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


def get_sus(account: Account) -> None:
    """Print the current service units for the given account

    Args:
        account: The account to inspect
    """

    account.check_has_proposal(raise_if=False)

    proposal_row = Session().query(Proposal).filter_by(account=account.account_name).first()
    print(f"type,{','.join(app_settings.clusters)}")
    sus = [str(getattr(proposal_row, c)) for c in app_settings.clusters]
    print(f"proposal,{','.join(sus)}")

    investor_sus = account.get_current_investor_sus()
    for row in investor_sus:
        print(f"investment,{row}")


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
