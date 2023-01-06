"""The ``cli.parsers`` module defines commandline parsers used to build the
application's commandline interface. Individual parsers are designed around
different services provided by the banking app.
"""

import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from typing import List

from .types import Date, NonNegativeInt
from .. import settings
from ..account_logic import AdminServices, AccountServices, ProposalServices, InvestmentServices
from ..system import Slurm


class BaseParser(ArgumentParser):
    """Base class used for building commandline parsers

    Extends functionality defined by the builtin ``ArgumentParser`` class.
    Subclasses should define their desired commandline interface (i.e., any
    subparsers or arguments) in their ``__init__`` method.
    """

    def parse_known_args(self, args: List[str] = None, namespace: Namespace = None) -> tuple[Namespace, list[str]]:
        """Parse and return commandline arguments

        This method wraps the parent class implementation and forwards parsing
        errors to the ``error`` method. The parent class already does this in
        some, but not all cases (e.g., type casting errors).

        Args:
            args: Optionally parse the given arguments instead of STDIN
            namespace: The namespace class to use for returned values

        Returns:
            Tuple containing a namespace of valid arguments and a dictionary of invalid ones
        """

        try:
            return super().parse_known_args(args, namespace)

        except Exception as exception:
            self.error(str(exception))

    def error(self, message: str) -> None:
        """Print the error message to STDOUT and exit

        If the application was called without any arguments, print the help text.

        Args:
            message: The error message

        Raises:
            ArgumentError: If the ``define_interface`` attribute is ``True``
        """

        if len(sys.argv) == 1:
            self.print_help()
            raise SystemExit(message)

        else:
            super().error(message)


class AdminParser(BaseParser):
    """Commandline interface for high level administrative services

    This parser acts as an interface for functionality provided by
    the ``account_logic.AdminServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the commandline parser and its associated interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser)

        cluster_argument = dict(
            dest='cluster',
            nargs='+',
            choices=list(Slurm.cluster_names()),
            help='list of clusters to check the lock state on'
        )

        # Update account status for all accounts
        update_status = subparsers.add_parser(
            name='update_status',
            help='close expired allocations and lock accounts without available SUs')
        update_status.set_defaults(function=AdminServices.update_account_status)

        # List locked accounts
        list_locked = subparsers.add_parser('list_locked', help='list all locked accounts')
        list_locked.add_argument('--clusters', **cluster_argument)
        list_locked.set_defaults(function=AdminServices.list_locked_accounts)

        # List unlocked accounts
        list_unlocked = subparsers.add_parser('list_unlocked', help='list all unlocked accounts')
        list_unlocked.add_argument('--clusters', **cluster_argument)
        list_unlocked.set_defaults(function=AdminServices.list_unlocked_accounts)


class AccountParser(BaseParser):
    """Commandline interface for administrating individual accounts

    This parser acts as an interface for functionality provided by
    the ``account_logic.AccountServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the commandline parser and its associated interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser)

        # Reusable definitions for arguments
        account_argument = dict(
            metavar='account',
            dest='self',
            type=AccountServices,
            help='the slurm account name')

        clusters_argument = dict(
            dest='clusters',
            nargs='+',
            choices=list(Slurm.cluster_names()))

        all_clusters_argument = dict(
            metavar='\b',
            dest='clusters',
            action='store_const',
            const=list(Slurm.cluster_names()))

        # Lock an account
        lock_parser = subparsers.add_parser('lock', help='lock an account from submitting jobs')
        lock_parser.set_defaults(function=AccountServices.lock)
        lock_parser.add_argument(**account_argument)
        lock_cluster = lock_parser.add_mutually_exclusive_group(required=True)
        lock_cluster.add_argument('--all-clusters', **all_clusters_argument, help='lock all available clusters')
        lock_cluster.add_argument('--clusters', **clusters_argument, help='list of clusters to lock the account on')

        # Unlock Account
        unlock_parser = subparsers.add_parser('unlock', help='Allow a slurm account to resume submitting jobs')
        unlock_parser.set_defaults(function=AccountServices.unlock)
        unlock_parser.add_argument(**account_argument)
        unlock_cluster = unlock_parser.add_mutually_exclusive_group(required=True)
        unlock_cluster.add_argument('--clusters', **clusters_argument, help='list of clusters to unlock the account on')
        unlock_cluster.add_argument('--all-clusters', **all_clusters_argument)

        # Fetch general account information
        info_parser = subparsers.add_parser('info', help='print account usage and allocation information')
        info_parser.set_defaults(function=AccountServices.info)
        info_parser.add_argument(**account_argument)


class ProposalParser(BaseParser):
    """Commandline interface for managing individual proposals

    This parser acts as an interface for functionality provided by
    the ``account_logic.ProposalServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the commandline parser and its associated interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser)

        # Reusable definitions for arguments
        safe_date_format = settings.date_format.replace('%', '')
        account_argument = dict(
            dest='self',
            metavar='account',
            type=ProposalServices,
            help='the slurm account name'
        )

        proposal_id_argument = dict(
            dest='proposal_id',
            metavar='ID',
            type=int,
            help='the proposal ID number')

        # Proposal creation
        create_parser = subparsers.add_parser('create', help='create a new proposal for an existing account')
        create_parser.set_defaults(function=ProposalServices.create)
        create_parser.add_argument(**account_argument)
        create_parser.add_argument(
            '--start',
            metavar='date',
            type=Date,
            default=datetime.today(),
            help=f'proposal start date ({safe_date_format}) - defaults to today')
        create_parser.add_argument(
            '--end',
            metavar='date',
            type=Date,
            help=f'proposal end date ({safe_date_format}) - defaults to 1 year from today')
        self._add_cluster_args(create_parser)

        # Proposal deletion
        delete_parser = subparsers.add_parser('delete', help='delete an existing proposal')
        delete_parser.set_defaults(function=ProposalServices.delete)
        delete_parser.add_argument(**account_argument)
        delete_parser.add_argument('--id', **proposal_id_argument, required=True)

        # Add SUs to a proposal
        add_parser = subparsers.add_parser('add_sus', help='add service units to an existing proposal')
        add_parser.set_defaults(function=ProposalServices.add_sus)
        add_parser.add_argument(**account_argument)
        add_parser.add_argument('--id', **proposal_id_argument)
        self._add_cluster_args(add_parser)

        # Remove SUs from a proposal
        subtract_parser = subparsers.add_parser(
            name='subtract_sus',
            help='subtract service units from an existing proposal')
        subtract_parser.set_defaults(function=ProposalServices.subtract_sus)
        subtract_parser.add_argument(**account_argument)
        subtract_parser.add_argument('--id', **proposal_id_argument)
        self._add_cluster_args(subtract_parser)

        # Modify proposal dates
        modify_date_parser = subparsers.add_parser(
            name='modify_date',
            help='change the start or end date of an existing proposal')
        modify_date_parser.set_defaults(function=ProposalServices.modify_date)
        modify_date_parser.add_argument(**account_argument)
        modify_date_parser.add_argument('--id', **proposal_id_argument)
        modify_date_parser.add_argument(
            '--start',
            metavar='date',
            type=Date,
            help=f'set a new proposal start date ({safe_date_format})')
        modify_date_parser.add_argument(
            '--end',
            metavar='date',
            type=Date,
            help=f'set a new proposal end date ({safe_date_format})')

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given commandline subparser

        Args:
            parser: The parser to add arguments to
        """

        su_argument = dict(metavar='su', type=NonNegativeInt, default=0)
        parser.add_argument('--all-clusters', **su_argument, help='service units awarded across all clusters')

        # Add per-cluster arguments for setting service units
        for cluster in Slurm.cluster_names():
            parser.add_argument(f'--{cluster}', **su_argument, help=f'service units awarded on the {cluster} cluster')


class InvestmentParser(BaseParser):
    """Commandline interface for managing individual investments

    This parser acts as an interface for functionality provided by
    the ``account_logic.InvestmentServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Instantiate the commandline parser and its associated interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser)

        # Reusable definitions for arguments
        safe_date_format = settings.date_format.replace("%", "")
        account_definition = dict(
            dest='self',
            metavar='account',
            type=InvestmentServices,
            help='the slurm account name')

        investment_id_definition = dict(
            dest='inv_id',
            metavar='ID',
            type=NonNegativeInt,
            help='the investment ID number')

        service_unit_definition = dict(
            dest='sus',
            metavar='su',
            type=NonNegativeInt,
            required=True,
            help='the number of service units')

        # Investment creation
        create_parser = subparsers.add_parser('create', help='create a new investment for an existing account')
        create_parser.set_defaults(function=InvestmentServices.create)
        create_parser.add_argument(**account_definition)
        create_parser.add_argument('--sus', **service_unit_definition)
        create_parser.add_argument(
            '--num_inv',
            metavar='N',
            type=NonNegativeInt,
            default=5,
            help='divide the service units across N sequential investments')
        create_parser.add_argument(
            '--start',
            metavar='date',
            type=Date,
            default=datetime.today(),
            help=f'start date for the investment ({safe_date_format}) - defaults to today')
        create_parser.add_argument(
            '--end',
            metavar='date',
            type=Date,
            help=f'investment end date ({safe_date_format}) - defaults to 1 year from today')

        # Investment Deletion
        delete_parser = subparsers.add_parser('delete', help='delete an existing investment')
        delete_parser.set_defaults(function=InvestmentServices.delete)
        delete_parser.add_argument(**account_definition)
        delete_parser.add_argument('--id', **investment_id_definition, required=True)

        # Add SUs to Investment
        add_parser = subparsers.add_parser('add_sus', help='add service units to an existing investment')
        add_parser.set_defaults(function=InvestmentServices.add_sus)
        add_parser.add_argument(**account_definition)
        add_parser.add_argument('--id', **investment_id_definition)
        add_parser.add_argument('--sus', **service_unit_definition)

        # Remove SUs from Investment
        subtract_parser = subparsers.add_parser(
            name='subtract_sus',
            help='subtract service units from an existing investment')
        subtract_parser.set_defaults(function=InvestmentServices.subtract_sus)
        subtract_parser.add_argument(**account_definition)
        subtract_parser.add_argument('--id', **investment_id_definition)
        subtract_parser.add_argument('--sus', **service_unit_definition)

        # Modify Investment Dates
        modify_date_parser = subparsers.add_parser(
            name='modify_date',
            help='change the start or end date of an existing investment')
        modify_date_parser.set_defaults(function=InvestmentServices.modify_date)
        modify_date_parser.add_argument(**account_definition)
        modify_date_parser.add_argument('--id', **investment_id_definition)
        modify_date_parser.add_argument(
            '--start',
            metavar='date',
            type=Date,
            help=f'set a new investment start date ({safe_date_format})')
        modify_date_parser.add_argument(
            '--end',
            metavar='date',
            type=Date,
            help=f'set a new investment end date ({safe_date_format})')

        advance_parser = subparsers.add_parser(
            name='advance',
            help='forward service units from future investments to a given investment')
        advance_parser.set_defaults(function=InvestmentServices.add_sus)
        advance_parser.add_argument(**account_definition)
        advance_parser.add_argument('--id', **investment_id_definition)
        advance_parser.add_argument('--sus', **service_unit_definition)
