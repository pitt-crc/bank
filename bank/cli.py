"""The ``cli`` module defines the command line interface for the parent
application. This module is effectively a wrapper around existing functionality
defined in the ``account_logic`` module.

Command line functions are grouped together by the service being administered.

.. code-block:: bash

   application.py <service> <action> --arguments

Each service is represented by a distinct class which handles the parsing
and evaluation of all actions related to that service. These classes are
ultimetly inherited by the ``CLIParser`` class, which acts as the primary
command line interface for interacting with the parent application as a whole.

.. note:: Parser classes in this module are based on the ``ArgumentParser``
  class from the `standard Python library <https://docs.python.org/3/library/argparse.html>`_.

Usage Example
-------------

Use the ``CLIParser`` object to parsing and evaluate command line arguments:

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

If you want to access the command line interface for just a single service
(E.g., for testing purposes) you can use the dedicated class for that service:

.. code-block:: python

   >>> from bank.cli import AdminSubParser
   >>>
   >>> admin_parser = AdminSubParser()
   >>> admin_parser.parse_args()

API Reference
-------------
"""

from __future__ import annotations

import abc
import sys
from argparse import ArgumentParser
from datetime import datetime

from . import settings
from .orm import ProposalEnum


class BaseSubParser(ArgumentParser):
    """Used to extend functionality of the builtin ``ArgumentParser`` class"""

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the command line interface and any necessary subparsers"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=ArgumentParser)
        self.define_interface(subparsers)

    @classmethod
    @abc.abstractmethod
    def define_interface(cls, parent_parser):
        pass


class AdminSubParser(BaseSubParser):
    """Command line parser for the ``admin`` service"""

    @classmethod
    def define_interface(cls, parent_parser):
        update_status = parent_parser.add_parser('update_status', help='Update account status and send pending notifications for a single account')
        update_status.add_argument('--account', dest='account_name')

        parent_parser.add_parser('run_maintenance', help='Update account status and send pending notifications for all accounts')


class AccountSubParser(BaseSubParser):
    """Command line parser for the ``account`` service"""

    @classmethod
    def define_interface(cls, parent_parser):
        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='Name of a slurm user account', required=True)

        slurm_lock = parent_parser.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        slurm_lock.add_argument('--account', **account_definition)

        slurm_unlock = parent_parser.add_parser('unlock', help='Allow a slurm account to resume submitting jobs')
        slurm_unlock.add_argument('--account', **account_definition)

        renew = parent_parser.add_parser('renew', help='Renew an account\'s proposal and rollover any is_expired investments')
        renew.add_argument('--account', **account_definition)

        info = parent_parser.add_parser('info', help='Print account usage and allocation information')
        info.add_argument('--account', **account_definition)


class ProposalSubParser(BaseSubParser):
    """Command line parser for the ``proposal`` service"""

    @classmethod
    def define_interface(cls, parent_parser):
        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='The parent slurm account')
        type_definition = dict(type=ProposalEnum.from_string, help='', choices=list(ProposalEnum))

        proposal_create = parent_parser.add_parser('create', help='Create a new proposal for an existing slurm account')
        proposal_create.add_argument('--account', **account_definition)
        proposal_create.add_argument('--type', **type_definition)
        cls._add_cluster_args(proposal_create)

        proposal_delete = parent_parser.add_parser('delete', help='Delete an existing account proposal')
        proposal_delete.add_argument('--account', **account_definition)

        proposal_add = parent_parser.add_parser('add', help='Add service units to an existing proposal')
        proposal_add.add_argument('--account', **account_definition)
        cls._add_cluster_args(proposal_add)

        proposal_subtract = parent_parser.add_parser('subtract', help='Subtract service units from an existing proposal')
        proposal_subtract.add_argument('--account', **account_definition)
        cls._add_cluster_args(proposal_subtract)

        proposal_overwrite = parent_parser.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        proposal_overwrite.add_argument('--account', **account_definition)
        proposal_overwrite.add_argument('--type', **type_definition)
        proposal_overwrite.add_argument('--start', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal start date')
        proposal_overwrite.add_argument('--end', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal end date')
        cls._add_cluster_args(proposal_overwrite)

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
        """

        for cluster in settings.clusters:
            parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)


class InvestmentParser(BaseSubParser):
    """Command line parser for the ``investment`` service"""

    @classmethod
    def define_interface(cls, parent_parser):
        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='The parent slurm account')
        investment_id_definition = dict(dest='inv_id', metavar='id', type=int, required=True, help='The investment proposal id')
        service_unit_definition = dict(type=int, help='The number of SUs you want to process', required=True)

        investment_create = parent_parser.add_parser('create', help='Create a new investment')
        investment_create.add_argument('--account', **account_definition)
        investment_create.add_argument('--sus', type=int, help='The number of SUs you want to insert', required=True)
        investment_create.add_argument('--num_inv', type=int, default=5, help='Optionally divide service units across n sequential investments')
        investment_create.add_argument('--duration', type=int, default=365, help='The length of each investment')

        investment_delete = parent_parser.add_parser('delete', help='Delete an existing investment')
        investment_delete.add_argument('--account', **account_definition)
        investment_delete.add_argument('--id', **investment_id_definition)

        investment_add = parent_parser.add_parser('add', help='Add service units to an existing investment')
        investment_add.add_argument('--account', **account_definition)
        investment_add.add_argument('--id', **investment_id_definition)
        investment_add.add_argument('--sus', **service_unit_definition)

        investment_subtract = parent_parser.add_parser('subtract', help='Subtract service units from an existing investment')
        investment_subtract.add_argument('--account', **account_definition)
        investment_subtract.add_argument('--id', **investment_id_definition)
        investment_subtract.add_argument('--sus', **service_unit_definition)

        investment_overwrite = parent_parser.add_parser('overwrite', help='Overwrite properties of an existing investment')
        investment_overwrite.add_argument('--account', **account_definition)
        investment_overwrite.add_argument('--id', **investment_id_definition)
        investment_overwrite.add_argument('--sus', type=int, help='The new number of SUs in the investment')
        investment_overwrite.add_argument('--start', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment start date')
        investment_overwrite.add_argument('--end', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment end date')

        investment_advance = parent_parser.add_parser('advance', help='Move service units from future investments to the current allocation')
        investment_advance.add_argument('--account', **account_definition)
        investment_advance.add_argument('--sus', **service_unit_definition)


class Application(ArgumentParser):
    """Command line parser used as the primary entry point for the parent application"""

    def __init__(self):

        super().__init__()
        subparsers = self.add_subparsers(parser_class=ArgumentParser)

        admin_parser = subparsers.add_parser('admin', help='Tools for general account management')
        admin_subparsers = admin_parser.add_subparsers(title="admin actions")
        AdminSubParser.define_interface(admin_subparsers)

        account_parser = subparsers.add_parser('account', help='Tools for general account management')
        account_subparsers = account_parser.add_subparsers(title="admin actions")
        AccountSubParser.define_interface(account_subparsers)

        proposal_parser = subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_subparsers = proposal_parser.add_subparsers(title="proposal actions")
        ProposalSubParser.define_interface(proposal_subparsers)

        investment_parser = subparsers.add_parser('investment', help='Administrative tools for user investments')
        investment_subparsers = investment_parser.add_subparsers(title="investment actions")
        InvestmentParser.define_interface(investment_subparsers)

    def error(self, message):
        """Print the error message to STDOUT and exit

        If the application was called without any arguments, print the help text.

        Args:
            message: The error message
        """

        if len(sys.argv) == 1:
            self.print_help()

        else:
            sys.stderr.write('ERROR: {}\n'.format(message))

        sys.exit(2)

    @classmethod
    def execute(cls) -> None:
        """Parse command line arguments and execute the application.

        This method is defined as a class method to provide an executable hook
        for the package setup.py file.
        """

        app = cls()
        cli_kwargs = vars(app.parse_args())

        try:
            print(cli_kwargs)

        except Exception as err:
            app.error(str(err))
