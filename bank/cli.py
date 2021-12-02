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

..note:: Parser classes in this module are based on the ``ArgumentParser``
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

from argparse import ArgumentParser
from datetime import datetime
from typing import List

from . import settings, system, dao
from .orm.enum import ProposalType

# Reusable definitions for command line arguments
_user = dict(dest='--user', nargs='?', help='Optionally create a user under the parent slurm account')
_notify = dict(dest='--notify', action='store_true', help='Optionally notify the account holder via email')
_ptype = dict(dest='--ptype', default='proposal', choices=ProposalType.valid_values, help='The proposal type')
_date = dict(dest='--date', nargs='?', type=lambda s: datetime.strptime(s, settings.date_format))
_sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
_inv_id = dict(dest='--id', type=int, help='The investment proposal id')


class BaseParser(ArgumentParser):
    """Parent class for all command line parsers"""

    def __init__(self) -> None:
        super().__init__()
        self.service_subparsers = self.add_subparsers(parser_class=ArgumentParser)

    def execute(self, args: List[str] = None) -> None:
        """Method used to evaluate the command line parser

        Parse command line arguments and evaluate the corresponding function.
        If arguments are not explicitly passed to this function, they are
        retrieved from the command line.

        Args:
            args: A list of command line arguments
        """

        # Get parsed arguments as a dictionary
        cli_kwargs = {k.lstrip('-'): v for k, v in vars(self.parse_args(args)).items()}
        arg_name, method_name = cli_kwargs.pop('function').split('.')
        getattr(cli_kwargs.pop(arg_name), method_name)(**cli_kwargs)


class AdminParser(BaseParser):
    """Command line parser for the ``admin`` service"""

    def __init__(self) -> None:
        super().__init__()
        admin_parser = self.service_subparsers.add_parser('admin', help='Tools for general system status')
        admin_subparsers = admin_parser.add_subparsers()

        info = admin_subparsers.add_parser('info', help='Print usage and allocation information')
        info.add_argument('account', help='The account to print information for')

        notify = admin_subparsers.add_parser('notify', help='Send any pending email notifications')
        notify.add_argument('account', help='The account to process notification for')


class SlurmParser(BaseParser):
    """Command line parser for the ``slurm`` service"""

    def __init__(self) -> None:
        super().__init__()
        slurm_parser = self.service_subparsers.add_parser('slurm', help='Administrative tools for slurm accounts')
        slurm_parser.add_argument('--account', type=system.SlurmAccount, help='The slurm account to administrate')

        slurm_subparsers = slurm_parser.add_subparsers(title="Slurm actions")
        slurm_create = slurm_subparsers.add_parser('create', help='Create a new slurm account')
        slurm_create.set_defaults(function='account.create')
        slurm_create.add_argument(**_user)

        slurm_delete = slurm_subparsers.add_parser('delete', help='Delete an existing slurm account')
        slurm_delete.set_defaults(function='account.delete')
        slurm_delete.add_argument(**_user)

        slurm_lock = slurm_subparsers.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        slurm_lock.set_defaults(function='account.lock')
        slurm_lock.add_argument(**_notify)

        slurm_unlock = slurm_subparsers.add_parser('unlock', help='Allow a slurm account to submit jobs')
        slurm_unlock.set_defaults(function='account.unlock')
        slurm_unlock.add_argument(**_notify)


class ProposalParser(BaseParser):
    """Command line parser for the ``proposal`` service"""

    def __init__(self) -> None:
        super().__init__()
        proposal_parser = self.service_subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_parser.add_argument('--account', type=dao.ProposalData, help='The parent slurm account')
        proposal_subparsers = proposal_parser.add_subparsers(title="Proposal actions")

        proposal_create = proposal_subparsers.add_parser('create', help='Create a new proposal for an existing slurm account')
        proposal_create.set_defaults(function='account.create')
        proposal_create.add_argument(**_ptype)
        self._add_cluster_args(proposal_create)

        proposal_delete = proposal_subparsers.add_parser('delete', help='Delete an existing account proposal')
        proposal_delete.set_defaults(function='account.delete')
        self._add_cluster_args(proposal_delete)

        proposal_add = proposal_subparsers.add_parser('add', help='Add service units to an existing proposal')
        proposal_add.set_defaults(function='account.add')
        self._add_cluster_args(proposal_add)

        proposal_subtract = proposal_subparsers.add_parser('subtract', help='Subtract service units from an existing proposal')
        proposal_subtract.set_defaults(function='account.subtract')
        self._add_cluster_args(proposal_subtract)

        proposal_overwrite = proposal_subparsers.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        proposal_overwrite.set_defaults(function='account.overwrite')
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


class InvestmentParser(BaseParser):
    """Command line parser for the ``investment`` service"""

    def __init__(self) -> None:
        super().__init__()
        investment_parser = self.service_subparsers.add_parser('investment', help='Administrative tools for user investments')
        investment_parser.add_argument('--account', type=dao.InvestorData, help='The parent slurm account')
        investment_subparsers = investment_parser.add_subparsers(title="Investment actions")

        investment_create = investment_subparsers.add_parser('create', help='Create a new investment')
        investment_create.set_defaults(function='account.create')
        investment_create.add_argument(**_sus)

        investment_delete = investment_subparsers.add_parser('delete', help='Delete an existing investment')
        investment_delete.set_defaults(function='account.delete')
        investment_delete.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_add = investment_subparsers.add_parser('add', help='Add service units to an existing investment')
        investment_add.set_defaults(function='account.add')
        investment_add.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_subtract = investment_subparsers.add_parser('subtract', help='Subtract service units from an existing investment')
        investment_subtract.set_defaults(function='account.subtract')
        investment_subtract.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)

        investment_overwrite = investment_subparsers.add_parser('overwrite', help='Overwrite properties of an existing investment')
        investment_overwrite.set_defaults(function='account.overwrite')
        investment_overwrite.add_argument(**_inv_id)
        investment_delete.add_argument(**_sus)
        investment_delete.add_argument(**_date)

        investment_advance = investment_subparsers.add_parser('advance', help='Move service units from future investments to the current allocation')
        investment_advance.set_defaults(function='account.advance')
        investment_advance.add_argument(**_sus)

        investment_renew = investment_subparsers.add_parser('renew', help='Rollover any expired investments')
        investment_renew.set_defaults(function='account.renew')


class CLIParser(AdminParser, SlurmParser, ProposalParser, InvestmentParser):
    """Command line parser used as the primary entry point for the parent application"""
