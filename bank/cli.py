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
from typing import List

from . import dao
from .settings import app_settings

# Reusable definitions for command line arguments
_account = dict(dest='--account', type=dao.Account, help='The associated slurm account')
_ptype = dict(dest='--ptype', type=str, help='The proposal type: proposal or class')
_date = dict(dest='--date', help=f'The proposal start date using the format {app_settings.date_format}')
_sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
_inv_id = dict(dest='--id', help='The investment proposal id')
_notify = dict(dest='--notify', type=bool, help='Send a notification to the corresponding user account', default=True)


class CLIParser(ArgumentParser):
    """Parser for command line arguments"""

    def __init__(self) -> None:
        super().__init__()
        self.subparsers = self.add_subparsers(parser_class=ArgumentParser)

        # For each command line subparser we:
        # 1) Create a new subparser instance and give it a name  (e.g. 'info')
        # 2) Define subparser arguments - add args for the service units of each cluster using ``include_clusters=True``
        # 3) Define the function to be evaluated by the subparser or indicate the name of a dao method to evaluate

        # Subparsers for account management and info

        parser_info = self.subparsers.add_parser('info')
        self._add_args_to_parser(parser_info, _account)
        parser_info.set_defaults(use_dao_method='print_allocation_info')

        parser_usage = self.subparsers.add_parser('usage')
        self._add_args_to_parser(parser_usage, _account)
        parser_usage.set_defaults(use_dao_method='print_usage_info')

        parser_reset_raw_usage = self.subparsers.add_parser('reset_raw_usage')
        self._add_args_to_parser(parser_reset_raw_usage, _account)
        parser_reset_raw_usage.set_defaults(use_dao_method='reset_raw_usage')

        parser_find_unlocked = self.subparsers.add_parser('find_unlocked')
        parser_find_unlocked.set_defaults(function=lambda: print('\n'.join(dao.Account.find_unlocked())))

        parser_lock_with_notification = self.subparsers.add_parser('lock_with_notification')
        self._add_args_to_parser(parser_lock_with_notification, _account, _notify)
        parser_lock_with_notification.set_defaults(function=lambda account: account.set_locked_state(True))

        parser_release_hold = self.subparsers.add_parser('release_hold')
        self._add_args_to_parser(parser_release_hold, _account)
        parser_release_hold.set_defaults(function=lambda account: account.set_locked_state(False))

        parser_check_proposal_end_date = self.subparsers.add_parser('check_proposal_end_date')
        self._add_args_to_parser(parser_check_proposal_end_date, _account)
        parser_check_proposal_end_date.set_defaults(use_dao_method='send_pending_alerts')

        # Subparsers for adding and modifying general service unit allocations

        parser_insert = self.subparsers.add_parser('insert', help='Add a proposal to a user for the first time.')
        self._add_args_to_parser(parser_insert, _account, _ptype, include_clusters=True)
        parser_insert.set_defaults(use_dao_method='create_proposal')

        parser_add = self.subparsers.add_parser('add',
                                                help='Add SUs to an existing user proposal on top of current values.')
        self._add_args_to_parser(parser_add, _account, include_clusters=True)
        parser_add.set_defaults(use_dao_method='add_allocation_sus')

        parser_change = self.subparsers.add_parser('modify', help="Update the properties of a given account/proposal")
        self._add_args_to_parser(parser_change, _account, _date, include_clusters=True)
        parser_change.set_defaults(use_dao_method='overwrite_allocation_sus')

        # Subparsers for adding and modifying investment accounts

        parser_investor = self.subparsers.add_parser('investor', help='Add an investment proposal to a given user')
        self._add_args_to_parser(parser_investor, _account, _sus)
        parser_investor.set_defaults(use_dao_method='create_investment')

        parser_investor_modify = self.subparsers.add_parser('investor_modify')
        self._add_args_to_parser(parser_investor_modify, _inv_id, _sus, _date)
        parser_investor_modify.set_defaults(use_dao_method='overwrite_investment_sus')

        parser_renewal = self.subparsers.add_parser('renewal', help='Like modify but rolls over active investments')
        self._add_args_to_parser(parser_renewal, _account, include_clusters=True)
        parser_renewal.set_defaults(use_dao_method='renewal')

        parser_withdraw = self.subparsers.add_parser('withdraw')
        self._add_args_to_parser(parser_withdraw, _account, _sus)
        parser_withdraw.set_defaults(use_dao_method='withdraw')

    @staticmethod
    def _add_args_to_parser(parser: ArgumentParser, *arg_definitions: dict, include_clusters: bool = False) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
            *arg_definitions: Dictionary with arguments for ``parser.add_argument``
        """

        for arg_def in arg_definitions:
            arg_def = arg_def.copy()
            parser.add_argument(**arg_def)

        if include_clusters:
            for cluster in app_settings.clusters:
                parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)

    def execute(self, args: List[str] = None) -> None:
        """Entry point for running the command line parser

        Parse command line arguments and evaluate the corresponding function

        Args:
            args: A list of command line arguments
        """

        cli_kwargs = vars(self.parse_known_args(args)[0])  # Get parsed arguments as a dictionary
        cli_kwargs = {k.lstrip('-'): v for k, v in cli_kwargs.items()}

        # If the ``use_dao_method`` value is set, then evalute a method of the ``account`` argument
        use_dao_method = cli_kwargs.pop('use_dao_method', None)
        if use_dao_method is not None:
            getattr(cli_kwargs.pop('account'), use_dao_method)(**cli_kwargs)

        else:
            cli_kwargs.pop('function')(**cli_kwargs)
