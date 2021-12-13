"""The ``cli`` module defines the command line interface for the parent
application. This module is effectively a command line accessible wrapper
around existing functionality defined in the ``dao`` module.

Command line functions are grouped together by the service being administered.

.. code-block:: bash

   application.py <service> <action> --arguments

Each service is represented by a distinct class which handles the parsing
and evaluation of all actions related to that service. These classes are
inherited by the ``CLIParser`` class, which acts as the primary command
line interface for interacting with the parent application as a whole.

.. note:: Parser classes in this module are based on the ``ArgumentParser``
  class from the `standard Python library <https://docs.python.org/3/library/argparse.html>`_.

Usage Example
-------------

Use the `CLIParser`` object to parsing and evaluate command line arguments:

.. code-block:: python

   >>> from bank.cli import CLIParser
   >>>
   >>> parser = CLIParser()
   >>>
   >>> # Parse command line arguments but do not evaluate the result
   >>> args = parser.parse_args()
   >>>
   >>> # Parse command line arguments AND evaluate the corresponding function
   >>> parser.execute()

API Reference
-------------
"""

from collections import OrderedDict
from argparse import ArgumentParser
from datetime import datetime
from typing import List

from . import settings, dao, system

_date = dict(dest='--date', nargs='?', type=lambda s: datetime.strptime(s, settings.date_format))
_sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
_inv_id = dict(dest='--id', type=int, help='The investment proposal id')


class AdminParser(dao.AdminServices, ArgumentParser):
    """Command line parser for the ``admin`` service"""

    def __init__(self) -> None:
        super(dao.AdminServices, self).__init__()
        subparsers = self._subparsers or self.add_subparsers(parser_class=ArgumentParser)
        admin_parser = subparsers.add_parser('admin', help='Tools for general system status')
        admin_subparsers = admin_parser.add_subparsers(title="admin  actions")

        info = admin_subparsers.add_parser('info', help='Print usage and allocation information')
        info.set_defaults(function=super(AdminParser, AdminParser).print_info)
        info.add_argument('account', help='The account to print information for')

        notify = admin_subparsers.add_parser('notify', help='Send any pending email notifications')
        notify.set_defaults(function=super(AdminParser, AdminParser).send_pending_alerts)
        notify.add_argument('account', help='The account to process notifications for')

        unlocked = admin_subparsers.add_parser('unlocked', help='List all unlocked user accounts')
        unlocked.set_defaults(function=super(AdminParser, AdminParser).find_unlocked)


class SlurmParser(system.SlurmAccount, ArgumentParser):
    """Command line parser for the ``slurm`` service"""

    def __init__(self) -> None:
        super(system.SlurmAccount, self).__init__()
        subparsers = self._subparsers or self.add_subparsers(parser_class=ArgumentParser)
        slurm_parser = subparsers.add_parser('slurm', help='Administrative tools for slurm accounts')
        slurm_subparsers = slurm_parser.add_subparsers(title="slurm actions")

        slurm_create = slurm_subparsers.add_parser('add_acc', help='Create a new slurm account')
        slurm_create.set_defaults(function=super(SlurmParser, SlurmParser).create_account)
        slurm_create.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')
        slurm_create.add_argument('--desc', type=dao.SlurmAccount, help='The description of the account')
        slurm_create.add_argument('--org', type=dao.SlurmAccount, help='The parent organization of the account')

        slurm_delete = slurm_subparsers.add_parser('delete_acc', help='Delete an existing slurm account')
        slurm_delete.set_defaults(function=super(SlurmParser, SlurmParser).delete_account)
        slurm_delete.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')

        slurm_add_user = slurm_subparsers.add_parser('add_user', help='Add a user to an existing slurm account')
        slurm_add_user.set_defaults(function=super(SlurmParser, SlurmParser).add_user)
        slurm_add_user.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')
        slurm_add_user.add_argument('--user', help='Optionally create a user under the parent slurm account')

        slurm_delete_user = slurm_subparsers.add_parser('delete_user', help='Remove a user to an existing slurm account')
        slurm_delete_user.set_defaults(function=super(SlurmParser, SlurmParser).delete_user)
        slurm_delete_user.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')
        slurm_delete_user.add_argument('--user', help='Optionally create a user under the parent slurm account')

        slurm_lock = slurm_subparsers.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        slurm_lock.set_defaults(function=super(SlurmParser, SlurmParser).set_locked_state, lock_state=True)
        slurm_lock.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')

        slurm_unlock = slurm_subparsers.add_parser('unlock', help='Allow a slurm account to submit jobs')
        slurm_unlock.set_defaults(function=super(SlurmParser, SlurmParser).set_locked_state, lock_state=False)
        slurm_unlock.add_argument('--account', type=dao.SlurmAccount, help='The slurm account to administrate')


class ProposalParser(dao.ProposalAccount, ArgumentParser):
    """Command line parser for the ``proposal`` service"""

    def __init__(self) -> None:
        super(dao.ProposalAccount, self).__init__()
        subparsers = self._subparsers or self.add_subparsers(parser_class=ArgumentParser)
        proposal_parser = subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_subparsers = proposal_parser.add_subparsers(title="proposal actions")

        proposal_create = proposal_subparsers.add_parser('create', help='Create a new proposal for an existing slurm account')
        proposal_create.set_defaults(function=super(ProposalParser, ProposalParser).create_proposal)
        proposal_create.add_argument('--account', type=dao.ProposalAccount, help='The parent slurm account')
        self._add_cluster_args(proposal_create)

        proposal_delete = proposal_subparsers.add_parser('delete', help='Delete an existing account proposal')
        proposal_delete.set_defaults(function=super(ProposalParser, ProposalParser).delete_proposal)
        proposal_delete.add_argument('--account', type=dao.ProposalAccount, help='The parent slurm account')
        self._add_cluster_args(proposal_delete)

        proposal_add = proposal_subparsers.add_parser('add', help='Add service units to an existing proposal')
        proposal_add.set_defaults(function=super(ProposalParser, ProposalParser).add)
        proposal_add.add_argument('--account', type=dao.ProposalAccount, help='The parent slurm account')
        self._add_cluster_args(proposal_add)

        proposal_subtract = proposal_subparsers.add_parser('subtract', help='Subtract service units from an existing proposal')
        proposal_subtract.set_defaults(function=super(ProposalParser, ProposalParser).subtract)
        proposal_subtract.add_argument('--account', type=dao.ProposalAccount, help='The parent slurm account')
        self._add_cluster_args(proposal_subtract)

        proposal_overwrite = proposal_subparsers.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        proposal_overwrite.set_defaults(function=super(ProposalParser, ProposalParser).overwrite)
        proposal_overwrite.add_argument('--account', type=dao.ProposalAccount, help='The parent slurm account')
        proposal_overwrite.add_argument(**_date)
        self._add_cluster_args(proposal_overwrite)

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
        """

        for cluster in settings.clusters:
            parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)


class InvestmentParser(dao.InvestorAccount, ArgumentParser):
    """Command line parser for the ``investment`` service"""

    def __init__(self) -> None:
        super(dao.InvestorAccount, self).__init__()
        subparsers = self._subparsers or self.add_subparsers(parser_class=ArgumentParser)
        investment_parser = subparsers.add_parser('investment', help='Administrative tools for user investments')
        investment_parser.add_argument('--account', type=dao.InvestorAccount, help='The parent slurm account')
        investment_subparsers = investment_parser.add_subparsers(title="investment actions")

        investment_create = investment_subparsers.add_parser('create', help='Create a new investment')
        investment_create.set_defaults(function=super(InvestmentParser, InvestmentParser).create_investment)
        investment_create.add_argument(**_sus)

        investment_delete = investment_subparsers.add_parser('delete', help='Delete an existing investment')
        investment_delete.set_defaults(function=super(InvestmentParser, InvestmentParser).delete_investment)
        investment_delete.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_add = investment_subparsers.add_parser('add', help='Add service units to an existing investment')
        investment_add.set_defaults(function=super(InvestmentParser, InvestmentParser).add)
        investment_add.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_subtract = investment_subparsers.add_parser('subtract', help='Subtract service units from an existing investment')
        investment_subtract.set_defaults(function=super(InvestmentParser, InvestmentParser).subtract)
        investment_subtract.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_overwrite = investment_subparsers.add_parser('overwrite', help='Overwrite properties of an existing investment')
        investment_overwrite.set_defaults(function=super(InvestmentParser, InvestmentParser).overwrite)
        investment_overwrite.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)
        investment_delete.add_argument(**_date)

        investment_advance = investment_subparsers.add_parser('advance', help='Move service units from future investments to the current allocation')
        investment_advance.set_defaults(function=super(InvestmentParser, InvestmentParser).advance)
        investment_advance.add_argument(**_sus)

        investment_renew = investment_subparsers.add_parser('renew', help='Rollover any expired investments')
        investment_renew.set_defaults(function=super(InvestmentParser, InvestmentParser).renew)


class CLIParser(AdminParser, SlurmParser, InvestmentParser, ProposalParser):
    """Command line parser used as the primary entry point for the parent application"""

    def execute(self, args: List[str] = None) -> None:
        """Method used to evaluate the command line parser

        Parse command line arguments and evaluate the corresponding function.
        If arguments are not explicitly passed to this function, they are
        retrieved from the command line.

        Args:
            args: A list of command line arguments
        """

        cli_kwargs = OrderedDict(self.parse_args(args)._get_kwargs())
        cli_kwargs.pop('function')(*cli_kwargs.values())
