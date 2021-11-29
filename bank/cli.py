"""The ``cli`` module defines the command line interface for the parent
application. This module is effectively a command line accessible wrapper
around existing functionality defined in the ``dao`` module.

Usage Example
-------------

The ``CLIParser`` object is an extension of the ``ArgumentParser`` class from
the `standard Python library <https://docs.python.org/3/library/argparse.html>`_.
It is responsible for both the parsing and evaluation  of command line arguments:

.. code-block:: python

   >>> from bank.cli import CLIParser
   >>>
   >>> parser = CLIParser()
   >>>
   >>> # Parse command line arguments but do not evaluate the result
   >>> args = parser.parse_args()
   >>>
   >>> # Parse command line arguments and evaluate the corresponding function
   >>> parser.execute()

API Reference
-------------
"""

from argparse import ArgumentParser
from datetime import datetime
from typing import List

from .settings import app_settings

# Reusable definitions for command line arguments
_account = dict(dest='--account', required=True, help='The slurm account to administrate')
_user = dict(dest='--user', nargs='?', help='Optionally create a user under the parent slurm account')
_notify = dict(dest='--notify', action='store_true', help='Optionally notify the account holder via email')
_ptype = dict(dest='--ptype', default='proposal', options=['proposal', 'class'], help='The proposal type')
_date = dict(dest='--date', nargs='?', type=lambda s: datetime.strptime(s, app_settings.date_format))
_sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
_inv_id = dict(dest='--id', type=int, help='The investment proposal id')


class CLIParser(ArgumentParser):
    def __init__(self) -> None:
        """Parser for command line arguments

        Parser arguments are broken down by the service being administered, the
        action being taken, and any arguments needed to evaluate that action:

        ``my_cli.py service action --options``

        For a complete usage description, use ``CLIParser().print_usage()``.
        """

        super().__init__()
        service_subparsers = self.add_subparsers(parser_class=ArgumentParser)

        info = service_subparsers.add_parser('info', help='Print usage and allocation information')
        info.add_argument('account', help='The account to print information for')

        notify = service_subparsers.add_parser('notify', help='Send any pending email notifications')
        notify.add_argument('account', help='The account to process notification for')

        # Parsers for the Slurm service
        slurm_parser = service_subparsers.add_parser('slurm', help='Administrative tools for slurm accounts')
        slurm_subparsers = slurm_parser.add_subparsers(title="Slurm actions")

        slurm_create = slurm_subparsers.add_parser('create', help='Create a new slurm account')
        self._add_args_to_parser(slurm_create, _account, _user)

        slurm_delete = slurm_subparsers.add_parser('delete', help='Delete an existing slurm account')
        self._add_args_to_parser(slurm_delete, _account, _user)

        slurm_lock = slurm_subparsers.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        self._add_args_to_parser(slurm_lock, _account, _notify)

        slurm_unlock = slurm_subparsers.add_parser('unlock', help='Allow a slurm account to submit jobs')
        self._add_args_to_parser(slurm_unlock, _account, _notify)

        # Parsers for user proposals
        proposal_parser = service_subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_subparsers = proposal_parser.add_subparsers(title="Proposal actions")

        proposal_create = proposal_subparsers.add_parser('create', help='Create a new proposal for an existing slurm account')
        self._add_args_to_parser(proposal_create, _account, _ptype, include_clusters=True)

        proposal_delete = proposal_subparsers.add_parser('delete', help='Delete an existing account proposal')
        self._add_args_to_parser(proposal_delete, _account, include_clusters=True)

        proposal_add = proposal_subparsers.add_parser('add', help='Add service units to an existing proposal')
        self._add_args_to_parser(proposal_add, _account, include_clusters=True)

        proposal_subtract = proposal_subparsers.add_parser('subtract', help='Subtract service units from an existing proposal')
        self._add_args_to_parser(proposal_subtract, _account, include_clusters=True)

        proposal_overwrite = proposal_subparsers.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        self._add_args_to_parser(proposal_overwrite, _account, _date, include_clusters=True)

        # Parsers for investments
        investment_parser = service_subparsers.add_parser('investment', help='Administrative tools for user investments')
        investment_subparsers = investment_parser.add_subparsers(title="Investment actions")

        investment_create = investment_subparsers.add_parser('create', description='Create a new investment')
        self._add_args_to_parser(investment_create, _account, _sus)

        investment_delete = investment_subparsers.add_parser('delete', description='Delete an existing investment')
        self._add_args_to_parser(investment_delete, _account, _inv_id, _sus)

        investment_add = investment_subparsers.add_parser('add', help='Add service units to an existing investment')
        self._add_args_to_parser(investment_add, _account, _inv_id, _sus)

        investment_subtract = investment_subparsers.add_parser('subtract', help='Subtract service units from an existing investment')
        self._add_args_to_parser(investment_subtract, _account, _inv_id, _sus)

        investment_overwrite = investment_subparsers.add_parser('overwrite', help='Overwrite properties of an existing investment')
        self._add_args_to_parser(investment_overwrite, _account, _inv_id, _sus, _date)

        investment_advance = investment_subparsers.add_parser('advance')
        self._add_args_to_parser(investment_advance, _account, _sus)

        investment_renew = investment_subparsers.add_parser('renew')
        self._add_args_to_parser(investment_renew, _account)

    @staticmethod
    def _add_args_to_parser(parser: ArgumentParser, *arg_definitions: dict, include_clusters: bool = False) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
            *arg_definitions: Dictionary with arguments for ``parser.add_argument``
            include_clusters: Dynamically add arguments from application settings for the service units of each cluster
        """

        for arg_def in arg_definitions:
            arg_def = arg_def.copy()
            parser.add_argument(**arg_def)

        if include_clusters:
            for cluster in app_settings.clusters:
                parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)

    def error(self, message):
        """Print a usage message to stderr raise the message as an exception.

        Raises:
            RuntimeError: Error that encapsulates the given message.
        """

        import sys
        self.print_usage(sys.stderr)
        raise RuntimeError(message)

    def execute(self, args: List[str] = None) -> None:
        """Entry point for running the command line parser

        Parse command line arguments and evaluate the corresponding function

        Args:
            args: A list of command line arguments
        """

        cli_kwargs = vars(self.parse_args(args))  # Get parsed arguments as a dictionary

        # If the ``use_dao_method`` value is set, then evaluate a method of the ``account`` argument
        use_arg_method = cli_kwargs.pop('use_arg_method', None)
        if use_arg_method is not None:
            arg_name, method_name = use_arg_method.split('.')
            getattr(cli_kwargs.pop(arg_name), method_name)(**cli_kwargs)

        else:
            cli_kwargs.pop('function')(**cli_kwargs)
