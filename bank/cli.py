"""The ``cli`` module defines the commandline interface for the parent application. This module is effectively
a wrapper around existing functionality defined in the ``account_logic`` module.

Commandline functions are grouped together by the service being administered.

.. code-block:: bash

   application.py <service> <action> --arguments

Each service is represented by a distinct class which handles the parsing of commands and arguments related to
that service. These classes are ultimatly called by the ``CommandLineApplication`` class, which acts as the
primary commandline interface for the parent application.

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
from argparse import ArgumentParser, ArgumentTypeError, ArgumentError, _SubParsersAction
from datetime import date, datetime
from typing import Type

from . import settings
from .account_logic import AccountServices, AdminServices, InvestmentServices, ProposalServices
from .system.slurm import Slurm


class ArgumentTypes:
    """Methods for type casting custom string formats into other data types"""

    @staticmethod
    def date(date_string: str) -> date:
        """Cast a string to a ``date`` object

        Args:
            date_string: The string value to cast

        Returns:
            The passed value as ``date`` instance
        """

        try:
            return datetime.strptime(date_string, settings.date_format).date()

        except Exception as excep:
            raise ArgumentTypeError(str(excep)) from excep

    @staticmethod
    def non_negative_int(int_string: str) -> int:
        """Cast a string to a positive ``int`` object

        Args:
            int_string: The string value to cast

        Returns:
            The passed value as an ``int`` instance

        Raises:
            ArgumentTypeError: If the integer value is less than zero
        """

        try:
            number = int(int_string)

        except Exception as excep:
            raise ArgumentTypeError(str(excep)) from excep

        if number < 0:
            raise ArgumentTypeError(f"{number} is negative. SUs must be a positive integer")

        return number


class BaseParser(ArgumentParser):
    """Abstract base class for building commandline parsers

    Subclasses must define their desired commandline interface (i.e., any
    subparsers or arguments) by implementing the ``define_interface`` method.
    The interface is automatically added to the parent parser instance at
    instantiation.
    """

    def __init__(self, *args, raise_on_error=True, **kwargs) -> None:
        """Instantiate a commandline parser and its associated interface

        Args:
            raise_on_error: Raise an exception instead of exiting out when an error occurs
        """

        super().__init__(*args, **kwargs)
        self.raise_on_error = raise_on_error

        subparsers = self.add_subparsers(parser_class=BaseParser)
        subparsers.raise_on_error = raise_on_error
        self.define_interface(subparsers)

    def error(self, message: str) -> None:
        """Print the error message to STDOUT and exit

        If the application was called without any arguments, print the help text.

        Args:
            message: The error message

        Raises:
            ArgumentError: If the ``define_interface`` attribute is ``True``
        """

        if self.raise_on_error:
            raise ArgumentError(None, message)

        if len(sys.argv) == 1:
            self.print_help()

        else:
            super().error(message)

    @classmethod
    @abc.abstractmethod
    def define_interface(cls, parent_parser: _SubParsersAction) -> None:
        """Define the commandline interface for the parent parser

        This method is implemented by subclasses to define the commandline
        interface for the parent parser instance. Subparsers and arguments
        should be assigned the ``parent_parser`` argument.

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """


class AdminParser(BaseParser):
    """Commandline interface for the ``AdminServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser: _SubParsersAction) -> None:
        """Define the commandline interface for the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        cluster_argument = dict(
            dest='cluster',
            nargs='+',
            choices=list(Slurm.cluster_names()),
            help='A cluster or list of clusters to lock the account on'
        )

        # Update Account Status
        update_status = parent_parser.add_parser(
            name='update_status',
            help='Close any expired proposals/investments and lock accounts for all unlocked accounts')
        update_status.set_defaults(function=AdminServices.update_account_status)

        # List Locked Accounts
        list_locked = parent_parser.add_parser(
            name='list_locked',
            help='List all of the accounts that are currently set to the locked state')
        list_locked.add_argument('--clusters', **cluster_argument)
        list_locked.set_defaults(function=AdminServices.list_locked_accounts)

        # List Unlocked Accounts
        list_unlocked = parent_parser.add_parser(
            name='list_unlocked',
            help='List all of the accounts that are currently set to the unlocked state')
        list_unlocked.add_argument('--clusters', **cluster_argument)
        list_unlocked.set_defaults(function=AdminServices.list_unlocked_accounts)


class AccountParser(BaseParser):
    """Commandline interface for the ``AccountServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser: _SubParsersAction) -> None:
        """Define the commandline interface for the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_argument = dict(
            metavar='account',
            dest='self',
            type=AccountServices,
            help='Name of a slurm account'
        )
        cluster_argument = dict(
            dest='clusters',
            nargs='+',
            choices=list(Slurm.cluster_names()),
            help='A cluster or list of clusters to lock the account on'
        )
        all_clusters_argument = dict(
            metavar='\b',
            dest='clusters',
            action='store_const',
            const=list(Slurm.cluster_names()),
            help='Use all clusters available on the system'
        )

        # Lock Account
        lock_parser = parent_parser.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        lock_parser.set_defaults(function=AccountServices.lock)
        lock_parser.add_argument(**account_argument)
        lock_cluster = lock_parser.add_mutually_exclusive_group(required=True)
        lock_cluster.add_argument('--clusters', **cluster_argument)
        lock_cluster.add_argument('--all_clusters', **all_clusters_argument)

        # Unlock Account
        unlock_parser = parent_parser.add_parser('unlock', help='Allow a slurm account to resume submitting jobs')
        unlock_parser.set_defaults(function=AccountServices.unlock)
        unlock_parser.add_argument(**account_argument)
        unlock_cluster = unlock_parser.add_mutually_exclusive_group(required=True)
        unlock_cluster.add_argument('--clusters', **cluster_argument)
        unlock_cluster.add_argument('--all_clusters', **all_clusters_argument)

        # Account information parser
        info_parser = parent_parser.add_parser('info', help='Print account usage and allocation information')
        info_parser.set_defaults(function=AccountServices.info)
        info_parser.add_argument(**account_argument)


class ProposalParser(BaseParser):
    """Commandline interface for the ``ProposalServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser: _SubParsersAction) -> None:
        """Define the commandline interface for the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_definition = dict(
            dest='self',
            metavar='account',
            type=ProposalServices,
            help='The parent slurm account'
        )
        proposal_id_definition = dict(
            dest='proposal_id',
            metavar='proposal_ID',
            type=int,
            help='The ID associated with a specific proposal on the account'
        )

        # Proposal Creation
        create_parser = parent_parser.add_parser('create', help='Create a new proposal for an existing slurm account')
        create_parser.set_defaults(function=ProposalServices.create)
        create_parser.add_argument(**account_definition)
        create_parser.add_argument(
            '--start',
            metavar='DATE',
            type=ArgumentTypes.date,
            default=datetime.today(),
            help=(
                'Start date for the proposal, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}, the default is today'
            )
        )
        create_parser.add_argument(
            '--end',
            metavar='DATE',
            type=ArgumentTypes.date,
            help='Duration of the proposal in months, default is 1 year (12 months)'
        )
        cls._add_cluster_args(create_parser)

        # Proposal Deletion
        delete_parser = parent_parser.add_parser('delete', help='Delete an existing proposal')
        delete_parser.set_defaults(function=ProposalServices.delete)
        delete_parser.add_argument(**account_definition)
        delete_parser.add_argument('--ID', **proposal_id_definition, required=True)

        # Add SUs to a Proposal
        add_parser = parent_parser.add_parser('add_sus', help='Add service units to an existing proposal')
        add_parser.set_defaults(function=ProposalServices.add_sus)
        add_parser.add_argument(**account_definition)
        add_parser.add_argument('--ID', **proposal_id_definition)
        cls._add_cluster_args(add_parser)

        # Remove SUs from Proposal
        subtract_parser = parent_parser.add_parser(
            'subtract_sus',
            help='Subtract service units from an existing proposal'
        )
        subtract_parser.set_defaults(function=ProposalServices.subtract_sus)
        subtract_parser.add_argument(**account_definition)
        subtract_parser.add_argument('--ID', **proposal_id_definition)
        cls._add_cluster_args(subtract_parser)

        # Modify Proposal Dates
        modify_date_parser = parent_parser.add_parser(
            'modify_date',
            help='Change the start or end date of an existing proposal'
        )
        modify_date_parser.set_defaults(function=ProposalServices.modify_date)
        modify_date_parser.add_argument(**account_definition)
        modify_date_parser.add_argument('--ID', **proposal_id_definition)
        modify_date_parser.add_argument(
            '--start',
            metavar='DATE',
            type=ArgumentTypes.date,
            help=(
                'Set a new proposal start date, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}'
            )
        )
        modify_date_parser.add_argument(
            '--end',
            metavar='DATE',
            type=ArgumentTypes.date,
            help=(
                'Set a new proposal end date, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}'
            )
        )

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given commandline subparser

        Args:
            parser: The parser to add arguments to
        """

        service_unit_definition = dict(
            metavar='service_units',
            type=ArgumentTypes.non_negative_int,
            default=0
        )
        # Add argument to specify Service Unit allotment
        for cluster in Slurm.cluster_names():
            parser.add_argument(
                f'--{cluster}',
                **service_unit_definition,
                help=f'Service Units awarded on the {cluster} cluster'
            )
        parser.add_argument(
            '--all_clusters',
            **service_unit_definition,
            help='Service Units awarded across all clusters'
        )


class InvestmentParser(BaseParser):
    """Commandline interface for the ``InvestmentServices`` class"""

    @classmethod
    def define_interface(cls, parent_parser) -> None:
        """Define the commandline interface for the parent parser

        Args:
            parent_parser: Subparser action to assign parsers and arguments to
        """

        # Reusable definitions for arguments
        account_definition = dict(
            dest='self',
            metavar='account',
            type=InvestmentServices,
            help='The parent slurm account'
        )
        investment_id_definition = dict(
            dest='inv_id',
            metavar='investment_ID',
            type=ArgumentTypes.non_negative_int,
            help='The investment proposal ID number'
        )
        service_unit_definition = dict(
            dest='sus',
            metavar='service_units',
            type=ArgumentTypes.non_negative_int,
            required=True,
            help='The number of SUs to process'
        )

        # Investment Creation
        create_parser = parent_parser.add_parser('create', help='Create a new investment')
        create_parser.set_defaults(function=InvestmentServices.create)
        create_parser.add_argument(**account_definition)
        create_parser.add_argument('--SUs', **service_unit_definition)
        create_parser.add_argument(
            '--num_inv',
            metavar='N',
            type=ArgumentTypes.non_negative_int,
            default=5,
            help='Divide the service units across N sequential investments'
        )
        create_parser.add_argument(
            '--start',
            metavar='DATE',
            type=ArgumentTypes.date,
            default=datetime.today(),
            help=(
                'Start date for the investment, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}, the default is today'
            )
        )
        create_parser.add_argument(
            '--end',
            metavar='DATE',
            type=ArgumentTypes.date,
            help=('The expiration date of the investment / first investment in a series. The default is a year '
                  'from the start date')
        )

        # Investment Deletion
        delete_parser = parent_parser.add_parser('delete', help='Delete an existing investment')
        delete_parser.set_defaults(function=InvestmentServices.delete)
        delete_parser.add_argument(**account_definition)
        delete_parser.add_argument('--ID', **investment_id_definition, required=True)

        # Add SUs to Investment
        add_parser = parent_parser.add_parser('add_sus', help='Add service units to an existing investment')
        add_parser.set_defaults(function=InvestmentServices.add_sus)
        add_parser.add_argument(**account_definition)
        add_parser.add_argument('--ID', **investment_id_definition)
        add_parser.add_argument('--SUs', **service_unit_definition)

        # Remove SUs from Investment
        subtract_parser = parent_parser.add_parser(
            'subtract_sus',
            help='Subtract service units from an existing investment'
        )
        subtract_parser.set_defaults(function=InvestmentServices.subtract_sus)
        subtract_parser.add_argument(**account_definition)
        subtract_parser.add_argument('--ID', **investment_id_definition)
        subtract_parser.add_argument('--SUs', **service_unit_definition)

        # Modify Investment Dates
        modify_date_parser = parent_parser.add_parser(
            'modify_date',
            help='Modify the start or end date of an existing investment'
        )
        modify_date_parser.set_defaults(function=InvestmentServices.modify_date)
        modify_date_parser.add_argument(**account_definition)
        modify_date_parser.add_argument('--ID', **investment_id_definition)
        modify_date_parser.add_argument(
            '--start',
            metavar='DATE',
            type=ArgumentTypes.date,
            help=(
                'Set a new investment start date, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}'
            )
        )
        modify_date_parser.add_argument(
            '--end',
            metavar='DATE',
            type=ArgumentTypes.date,
            help=(
                'Set a new investment start date, '
                f'format: {datetime.strftime(datetime.today(), settings.date_format)}'
            )
        )

        advance_parser = parent_parser.add_parser(
            'advance',
            help='Move service units from future investments to the current allocation'
        )
        advance_parser.set_defaults(function=InvestmentServices.add_sus)
        advance_parser.add_argument(**account_definition)
        advance_parser.add_argument('--ID', **investment_id_definition)
        advance_parser.add_argument('--SUs', **service_unit_definition)


class CommandLineApplication:
    """commandline application used as the primary entry point for the parent application"""

    def __init__(self):
        """Initialize the application's commandline interface"""

        self.parser = ArgumentParser()
        self.subparsers = self.parser.add_subparsers(parser_class=ArgumentParser, dest='service', required=True)

        # Add desired parsers to the commandline application
        self.add_subparser_to_app(
            'admin',
            AdminParser,
            title='Admin actions',
            help_text='Tools for general account management'
        )
        self.add_subparser_to_app(
            'account',
            AccountParser,
            title='Account actions',
            help_text='Tools for general account management'
        )
        self.add_subparser_to_app(
            'proposal',
            ProposalParser,
            title='Proposal actions',
            help_text='Administrative tools for user proposals'
        )
        self.add_subparser_to_app(
            'investment',
            InvestmentParser,
            title='Investment actions',
            help_text='Administrative tools for user investments'
        )

    def add_subparser_to_app(
            self,
            command: str,
            parser_class: Type[BaseParser],
            title: str,
            help_text: str
    ) -> None:
        """Add a parser object to the parent commandline application as a subparser

        Args:
            command: The commandline argument used to invoke the given parser
            parser_class: A ``BaseParser`` subclass
            title: The help text title
            help_text: The help text description
        """

        parser = self.subparsers.add_parser(command, help=help_text)
        subparsers = parser.add_subparsers(title=title, dest='command', required=True)
        parser_class.define_interface(subparsers)

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute the application.

        This method is defined as a class method to provide an executable hook
        for the packaged setup.py file.
        """

        cli_kwargs = vars(cls().parser.parse_args())
        executable = cli_kwargs.pop('function')

        # Remove arguments unused in app logic
        del cli_kwargs['service']
        del cli_kwargs['command']

        # Execute app logic with relevant arguments
        executable(**cli_kwargs)
