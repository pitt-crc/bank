"""The ``cli`` module defines the commandline interface for the parent
application. This module is effectively a wrapper around existing functionality
defined in the ``account_logic`` module.

Commandline functions are grouped together by the service being administered.

.. code-block:: bash

   application.py <service> <action> --arguments

Each service is represented by a distinct class which handles the parsing
of commands and arguments related to that service. These classes are ultimetly
called by the ``CommandLineApplication`` class, which acts as the primary
commandline interface for the parent application.

.. note::
   Parser classes in this module are based on the ``ArgumentParser``
   class from the `standard Python library <https://docs.python.org/3/library/argparse.html>`_.

Usage Example
-------------

Use the ``CommandLineApplication`` object to parse and evaluate commandline arguments:

.. code-block:: python

   >>> from bank.cli import CommandLineApplication
   >>>
   >>> app = CommandLineApplication()
   >>>
   >>> # Parse commandline arguments and launch the banking application
   >>> app.execute()

The application's argument parsing functionality is accessible via the
``parser`` attribute:

.. code-block:: python

   >>> # Raise an error if there are unknown args
   >>> args = app.parser.parse_args()

If you want to access the commandline interface for just a single service
(e.g., for testing purposes) you can use the dedicated class for that service:

.. code-block:: python

   >>> from bank.cli import AdminParser
   >>>
   >>> admin_parser = AdminParser()
   >>> admin_parser.parse_args()

API Reference
-------------
"""

from __future__ import annotations

import abc
import sys
from argparse import ArgumentParser
from datetime import datetime
from typing import Type

from . import settings
from .account_logic import AdminServices, AccountServices, ProposalServices, InvestmentServices
from .orm import ProposalEnum
from .system import SlurmAccount


class BaseParser(ArgumentParser):
    """Abstract base class to use when building commandline parser objects

    Subclasses must define the commandline interface (i.e., any commandline
    subparsers or arguments) by implementing the ``define_interface`` method.
    The interface is automatically added to the parser object at installation.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the commandline interface and add any necessary subparsers"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=ArgumentParser)
        self.define_interface(subparsers)

    def error(self, message: str) -> None:
        """Print the error message to STDOUT and exit

        If the application was called without any arguments, print the help text.

        Args:
            message: The error message
        """

        if len(sys.argv) == 1:
            self.print_help()

        else:
            super().error(message)

    @classmethod
    @abc.abstractmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface of the parent parser

        Adds parsers and commandline arguments to the given subparser action.
        The ``parent_parser`` object is the same object returned by the
        ``add_subparsers`` method.

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """


class AdminParser(BaseParser):
    """Commandline interface for the ``AdminServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface of the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        update_status = parent_parser.add_parser('update_status', help='Update account status and send pending notifications for a single account')
        update_status.set_defaults(function=AdminServices.update_account_status)

        maintenance_parser = parent_parser.add_parser('run_maintenance', help='Update account status and send pending notifications for all accounts')
        maintenance_parser.set_defaults(function=AdminServices.run_maintenance)


class AccountParser(BaseParser):
    """Commandline interface for the ``AccountServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface of the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_argument = dict(metavar='acc', dest='self',  type=AccountServices, help='Name of a slurm user account', required=True)

        lock_parser = parent_parser.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        lock_parser.set_defaults(function=AccountServices.lock_account)
        lock_parser.add_argument('--account', **account_argument)

        unlock_parser = parent_parser.add_parser('unlock', help='Allow a slurm account to resume submitting jobs')
        unlock_parser.set_defaults(function=AccountServices.unlock_account)
        unlock_parser.add_argument('--account', **account_argument)

        renew_parser = parent_parser.add_parser('renew', help='Renew an account\'s proposal and rollover any is_expired investments')
        renew_parser.set_defaults(function=AccountServices.renew)
        renew_parser.add_argument('--account', **account_argument)

        info_parser = parent_parser.add_parser('info', help='Print account usage and allocation information')
        info_parser.set_defaults(function=AccountServices.print_info)
        info_parser.add_argument('--account', **account_argument)


class ProposalParser(BaseParser):
    """Commandline interface for the ``ProposalServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface of the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='The parent slurm account')
        type_definition = dict(type=ProposalEnum.from_string, help='', choices=list(ProposalEnum))

        create_parser = parent_parser.add_parser('create', help='Create a new proposal for an existing slurm account')
        create_parser.set_defaults(function=ProposalServices.create_proposal)
        create_parser.add_argument('--account', **account_definition)
        create_parser.add_argument('--type', **type_definition)
        cls._add_cluster_args(create_parser)

        delete_parser = parent_parser.add_parser('delete', help='Delete an existing account proposal')
        delete_parser.set_defaults(function=ProposalServices.delete_proposal)
        delete_parser.add_argument('--account', **account_definition)

        add_parser = parent_parser.add_parser('add', help='Add service units to an existing proposal')
        add_parser.set_defaults(function=ProposalServices.add_sus)
        add_parser.add_argument('--account', **account_definition)
        cls._add_cluster_args(add_parser)

        subtract_parser = parent_parser.add_parser('subtract', help='Subtract service units from an existing proposal')
        subtract_parser.set_defaults(function=ProposalServices.subtract_sus)
        subtract_parser.add_argument('--account', **account_definition)
        cls._add_cluster_args(subtract_parser)

        overwrite_parser = parent_parser.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        overwrite_parser.set_defaults(function=ProposalServices.modify_proposal)
        overwrite_parser.add_argument('--account', **account_definition)
        overwrite_parser.add_argument('--type', **type_definition)
        overwrite_parser.add_argument('--start', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal start date')
        overwrite_parser.add_argument('--end', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal end date')
        cls._add_cluster_args(overwrite_parser)

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given commandline subparser

        Args:
            parser: The parser to add arguments to
        """

        for cluster in settings.clusters:
            parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)


class InvestmentParser(BaseParser):
    """Commandline interface for the ``InvestmentServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface of the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='The parent slurm account')
        investment_id_definition = dict(dest='inv_id', metavar='id', type=int, required=True, help='The investment proposal id')
        service_unit_definition = dict(type=int, help='The number of SUs you want to process', required=True)

        create_parser = parent_parser.add_parser('create', help='Create a new investment')
        create_parser.set_defaults(function=InvestmentServices.create_investment)
        create_parser.add_argument('--account', **account_definition)
        create_parser.add_argument('--sus', type=int, help='The number of SUs you want to insert', required=True)
        create_parser.add_argument('--num_inv', type=int, default=5, help='Optionally divide service units across n sequential investments')
        create_parser.add_argument('--duration', type=int, default=365, help='The length of each investment')

        delete_parser = parent_parser.add_parser('delete', help='Delete an existing investment')
        delete_parser.set_defaults(function=InvestmentServices.delete_investment)
        delete_parser.add_argument('--account', **account_definition)
        delete_parser.add_argument('--id', **investment_id_definition)

        add_parser = parent_parser.add_parser('add', help='Add service units to an existing investment')
        add_parser.set_defaults(function=InvestmentServices.add_sus)
        add_parser.add_argument('--account', **account_definition)
        add_parser.add_argument('--id', **investment_id_definition)
        add_parser.add_argument('--sus', **service_unit_definition)

        subtract_parser = parent_parser.add_parser('subtract', help='Subtract service units from an existing investment')
        subtract_parser.set_defaults(function=InvestmentServices.subtract_sus)
        subtract_parser.add_argument('--account', **account_definition)
        subtract_parser.add_argument('--id', **investment_id_definition)
        subtract_parser.add_argument('--sus', **service_unit_definition)

        overwrite_parser = parent_parser.add_parser('overwrite', help='Overwrite properties of an existing investment')
        overwrite_parser.set_defaults(function=InvestmentServices.modify_investment)
        overwrite_parser.add_argument('--account', **account_definition)
        overwrite_parser.add_argument('--id', **investment_id_definition)
        overwrite_parser.add_argument('--sus', type=int, help='The new number of SUs in the investment')
        overwrite_parser.add_argument('--start', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment start date')
        overwrite_parser.add_argument('--end', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment end date')

        advance_parser = parent_parser.add_parser('advance', help='Move service units from future investments to the current allocation')
        advance_parser.set_defaults(function=InvestmentServices.add_sus)
        advance_parser.add_argument('--id', **investment_id_definition)
        advance_parser.add_argument('--account', **account_definition)
        advance_parser.add_argument('--sus', **service_unit_definition)


class CommandLineApplication:
    """commandline application used as the primary entry point for the parent application"""

    def __init__(self):
        """Initialize the application's commandline interface"""

        self.parser = ArgumentParser()
        self.subparsers = self.parser.add_subparsers(parser_class=ArgumentParser)

        # Add desired parsers to the commandline application
        self.add_subparser_to_app('admin', AdminParser, title='Admin actions', help_text='Tools for general account management')
        self.add_subparser_to_app('account', AccountParser, title='Account actions', help_text='Tools for general account management')
        self.add_subparser_to_app('proposal', ProposalParser, title='Proposal actions', help_text='Administrative tools for user proposals')
        self.add_subparser_to_app('investment', InvestmentParser, title='Investment actions', help_text='Administrative tools for user investments')

    def add_subparser_to_app(self, command: str, parser_class: Type[BaseParser], title: str, help_text: str) -> None:
        """Add a parser object to the parent commandline application as a subparser

        Args:
            command: The commandline argument used to invoke the given parser
            parser_class: A ``BaseParser`` subclass
            title: The help text title
            help_text: The help text description
        """

        parser = self.subparsers.add_parser(command, help=help_text)
        subparsers = parser.add_subparsers(title=title)
        parser_class.define_interface(subparsers)

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute the application.

        This method is defined as a class method to provide an executable hook
        for the packaged setup.py file.
        """

        cli_kwargs = vars(cls().parser.parse_args())
        executable = cli_kwargs.pop('function')
        executable(**cli_kwargs)
