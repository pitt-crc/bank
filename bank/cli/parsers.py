"""The ``cli.parsers`` module defines commandline parsers used to build the
application's commandline interface. Individual parsers are designed around
different services provided by the banking app.
"""
import sys
from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from datetime import datetime
from typing import List, Tuple

from bank import settings
from bank.account_logic import AdminServices, AccountServices, ProposalServices, InvestmentServices
from bank.system import Slurm
from .types import Date, NonNegativeInt


class BaseParser(ArgumentParser):
    """Abstract base class used for building commandline parsers """

    def parse_known_args(self, args: List[str] = None, namespace: Namespace = None) -> Tuple[Namespace, List[str]]:
        """Parse and return commandline arguments

        This method wraps the parent class implementation and forwards parsing
        errors to the ``error`` method. The parent class already does this in
        some, but not all cases (e.g., type casting errors).

        Args:
            args: Optionally parse the given arguments instead of parsing STDIN
            namespace: The namespace class to use for returned values

        Returns:
            Tuple with a namespace of valid arguments and a dictionary of invalid ones
        """

        try:
            return super().parse_known_args(args, namespace)

        except Exception as exception:
            self.error(str(exception))

    def error(self, message: str) -> None:
        """Exit the parser by raising a ``SystemExit`` error

        Print the help text before exiting when the parser is called with a missing argument.

        Args:
            message: The error message

        Raises:
            SystemExit: Every time the method is called
        """

        # If missing arguments, print help text followed by the error message
        if 'the following arguments are required:' in message:
            self.print_help()
            sys.stdout.write('\n')
            raise SystemExit(message)

        raise SystemExit(message)


class AdminParser(BaseParser):
    """Commandline interface for high level administrative services

    This parser acts as an interface for the ``account_logic.AdminServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Define the commandline interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser, required=True)

        # Reusable argument definitions
        cluster_argument = dict(
            dest='cluster',
            choices=list(Slurm.cluster_names()),
            help='the cluster to inspect'
        )

        # Update account status for all accounts
        update_status = subparsers.add_parser(
            name='update_status',
            help='close expired allocations and lock accounts without available SUs')
        update_status.set_defaults(function=AdminServices.update_account_status)

        # List locked accounts
        list_locked = subparsers.add_parser('list_locked', help='list all locked accounts')
        list_locked.add_argument('--cluster', **cluster_argument, required=True)
        list_locked.set_defaults(function=AdminServices.list_locked_accounts)

        # List unlocked accounts
        list_unlocked = subparsers.add_parser('list_unlocked', help='list all unlocked accounts')
        list_unlocked.add_argument('--cluster', **cluster_argument, required=True)
        list_unlocked.set_defaults(function=AdminServices.list_unlocked_accounts)


class AccountParser(BaseParser):
    """Commandline interface for administrating individual accounts

    This parser acts as an interface for the ``account_logic.AccountServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Define the commandline interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser, required=True)

        # Reusable argument definitions
        account_argument = dict(
            metavar='account',
            dest='self',
            type=AccountServices,
            help='the Slurm account name')

        clusters = list(Slurm.cluster_names())
        clusters_argument = dict(
            dest='clusters',
            nargs='+',
            choices=clusters)

        all_clusters_argument = dict(
            metavar='\b',
            dest='clusters',
            action='store_const',
            const=clusters)

        # Lock an account
        lock_parser = subparsers.add_parser('lock', help='lock an account from submitting jobs')
        lock_parser.set_defaults(function=AccountServices.lock)
        lock_parser.add_argument(**account_argument)
        lock_cluster = lock_parser.add_mutually_exclusive_group(required=True)
        lock_cluster.add_argument('--all-clusters', **all_clusters_argument, help='lock all available clusters')
        lock_cluster.add_argument('--clusters', **clusters_argument, help='list of clusters to lock the account on')

        # Unlock an account
        unlock_parser = subparsers.add_parser('unlock', help='allow a Slurm account to resume submitting jobs')
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

    This parser acts as an interface for the ``account_logic.ProposalServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Define the commandline interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser, required=True)

        # Reusable argument definitions
        safe_date_format = settings.date_format.replace('%', '')
        account_argument = dict(
            dest='self',
            metavar='account',
            type=ProposalServices,
            help='the Slurm account name'
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
        create_parser.add_argument(
            '--force',
            action=BooleanOptionalAction,
            help=f"boolean flag for whether or not to set the existing proposal to inactive and substitute a proposal "
                 f"with the provided values in it's place - default is False"
        )
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

        # Subtract SUs from a proposal
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
        modify_date_parser.add_argument(
            '--force',
            action=BooleanOptionalAction,
            help=f"boolean flag for whether or not to overwrite the existing proposal's dates, even if it "
                 f"would otherwise cause date range overlap - default is False"
        )

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given commandline subparser

        Args:
            parser: The parser to add arguments to
        """

        su_argument = dict(metavar='su', type=NonNegativeInt, default=0)
        parser.add_argument('--all-clusters', **su_argument, help='service units awarded across all clusters')

        # Add per-cluster arguments for setting service units
        for cluster in settings.clusters:
            parser.add_argument(f'--{cluster}', **su_argument, help=f'service units awarded on the {cluster} cluster')


class InvestmentParser(BaseParser):
    """Commandline interface for managing individual investments

    This parser acts as an interface for the ``account_logic.InvestmentServices`` class.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Define the commandline interface"""

        super().__init__(*args, **kwargs)
        subparsers = self.add_subparsers(parser_class=BaseParser, required=True)

        # Reusable argument definitions
        safe_date_format = settings.date_format.replace("%", "")
        account_definition = dict(
            dest='self',
            metavar='account',
            type=InvestmentServices,
            help='the Slurm account name')

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
            default=1,
            help='divide the service units across N sequential investments')
        create_parser.add_argument(
            '--start',
            metavar='date',
            type=Date,
            default=datetime.today(),
            help=f'investment start date ({safe_date_format}) - defaults to today')
        create_parser.add_argument(
            '--end',
            metavar='date',
            type=Date,
            help=f'investment end date ({safe_date_format}) - defaults to 1 year from today')

        # Investment deletion
        delete_parser = subparsers.add_parser('delete', help='delete an existing investment')
        delete_parser.set_defaults(function=InvestmentServices.delete)
        delete_parser.add_argument(**account_definition)
        delete_parser.add_argument('--id', **investment_id_definition, required=True)

        # Add SUs to an investment
        add_parser = subparsers.add_parser('add_sus', help='add service units to an existing investment')
        add_parser.set_defaults(function=InvestmentServices.add_sus)
        add_parser.add_argument(**account_definition)
        add_parser.add_argument('--id', **investment_id_definition)
        add_parser.add_argument('--sus', **service_unit_definition)

        # Subtract SUs from an investment
        subtract_parser = subparsers.add_parser(
            name='subtract_sus',
            help='subtract service units from an existing investment')
        subtract_parser.set_defaults(function=InvestmentServices.subtract_sus)
        subtract_parser.add_argument(**account_definition)
        subtract_parser.add_argument('--id', **investment_id_definition)
        subtract_parser.add_argument('--sus', **service_unit_definition)

        # Modify investment dates
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

        # Advance investment SUs
        advance_parser = subparsers.add_parser(
            name='advance',
            help='forward service units from future investments to a given investment')
        advance_parser.set_defaults(function=InvestmentServices.advance)
        advance_parser.add_argument(**account_definition)
        advance_parser.add_argument('--id', **investment_id_definition)
        advance_parser.add_argument('--sus', **service_unit_definition)
