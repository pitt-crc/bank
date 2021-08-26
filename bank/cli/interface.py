"""Functions used to support the application command line interface"""

import json

from ..dao import Account


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
