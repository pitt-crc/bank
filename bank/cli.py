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
from pathlib import Path
from typing import List

from . import dao
from .settings import app_settings

# Reusable definitions for command line arguments
account = dict(dest='--account', type=dao.Account, help='The associated slurm account')
prop_type = dict(dest='--type', type=str, help='The proposal type: proposal or class')
date = dict(dest='--date', help='The proposal start date (e.g 12/01/19)')
sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
proposal = dict(dest='--proposal', type=Path, help='Path of the proposal table in JSON format')
investor = dict(dest='--investor', type=Path, help='Path of the investor table in JSON format')
proposal_arch = dict(dest='--proposal_archive', type=Path, help='Path of the proposal archive table in JSON format')
investor_arch = dict(dest='--investor_archive', type=Path, help='Path of the investor archive table in JSON format')
allocated = dict(dest='--path', type=Path, help='Path of the exported file')
overwrite = dict(dest='-y', action='store_true', help='Automatically overwrite table data')
inv_id = dict(dest='--id', help='The investment proposal id')


class CLIParser(ArgumentParser):
    """Parser for command line arguments"""

    def __init__(self) -> None:
        super().__init__()
        self.subparsers = self.add_subparsers(parser_class=ArgumentParser)

        # Subparsers for account management and info

        parser_info = self.subparsers.add_parser('info')
        self._add_args_to_parser(parser_info, account)
        parser_info.set_defaults(function=lambda account, **kwargs: account.print_allocation_info(**kwargs))

        parser_usage = self.subparsers.add_parser('usage')
        self._add_args_to_parser(parser_usage, account)
        parser_usage.set_defaults(function=lambda account, *args, **kwargs: account.print_usage_info(*args, **kwargs))

        parser_reset_raw_usage = self.subparsers.add_parser('reset_raw_usage')
        self._add_args_to_parser(parser_reset_raw_usage, account)
        parser_reset_raw_usage.set_defaults(function=lambda account, **kwargs: account.reset_raw_usage(**kwargs))

        parser_find_unlocked = self.subparsers.add_parser('find_unlocked')
        parser_find_unlocked.set_defaults(function=lambda: print('\n'.join(dao.Bank.find_unlocked())))

        parser_lock_with_notification = self.subparsers.add_parser('lock_with_notification')
        self._add_args_to_parser(parser_lock_with_notification, account)
        parser_lock_with_notification.set_defaults(function=lambda account: account.set_locked_state(True))

        parser_release_hold = self.subparsers.add_parser('release_hold')
        self._add_args_to_parser(parser_release_hold, account)
        parser_release_hold.set_defaults(function=lambda account: account.set_locked_state(False))

        parser_check_proposal_end_date = self.subparsers.add_parser('check_proposal_end_date')
        self._add_args_to_parser(parser_check_proposal_end_date, account)
        parser_check_proposal_end_date.set_defaults(
            function=lambda account, **kwargs: account.send_pending_alerts(**kwargs))

        # Subparsers for adding and modifying general service unit allocations

        parser_insert = self.subparsers.add_parser('insert', help='Add a proposal to a user for the first time.')
        self._add_args_to_parser(parser_insert, prop_type, account, include_clusters=True)
        parser_insert.set_defaults(function=dao.Bank.create_proposal)

        parser_add = self.subparsers.add_parser('add', help='Add SUs to an existing user proposal on top of current values.')
        self._add_args_to_parser(parser_add, account, include_clusters=True)
        parser_add.set_defaults(function=lambda account, **kwargs: account.add_sus(**kwargs))

        parser_change = self.subparsers.add_parser('modify', help="Update the properties of a given account/proposal")
        self._add_args_to_parser(parser_change, account, include_clusters=True)
        parser_change.set_defaults(function=lambda account, **kwargs: account.modify_sus(**kwargs))

        # Subparsers for adding and modifying investment accounts

        parser_investor = self.subparsers.add_parser('investor', help='Add an investment proposal to a given user')
        self._add_args_to_parser(parser_investor, account, sus)
        parser_investor.set_defaults(function=dao.Bank.create_investment)

        parser_investor_modify = self.subparsers.add_parser('investor_modify')
        self._add_args_to_parser(parser_investor, inv_id, sus)
        parser_investor_modify.set_defaults(function=lambda account, **kwargs: account.modify_investment(**kwargs))

        parser_renewal = self.subparsers.add_parser('renewal', help='Like modify but rolls over active investments')
        self._add_args_to_parser(parser_renewal, account, include_clusters=True)
        parser_renewal.set_defaults(function=lambda account, **kwargs: account.renewal(**kwargs))

        parser_withdraw = self.subparsers.add_parser('withdraw')
        self._add_args_to_parser(parser_withdraw, account, sus)
        parser_withdraw.set_defaults(function=lambda account, **kwargs: account.withdraw(**kwargs))

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
        cli_kwargs.pop('function')(**cli_kwargs)
