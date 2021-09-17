from argparse import ArgumentParser
from functools import partial
from pathlib import Path

from bank.cli import functions

# Reusable definitions for command line arguments
account = dict(dest='--account', type=str, help='The associated slurm account')
prop_type = dict(dest='--type', type=str, help='The proposal type: proposal or class')
date = dict(dest='--date', help='The proposal start date (e.g 12/01/19)')
sus = dict(dest='--sus', type=int, help='The number of SUs you want to insert')
proposal = dict(dest='--proposal', type=Path, help='Path of the proposal table in JSON format')
investor = dict(dest='--investor', type=Path, help='Path of the investor table in JSON format')
proposal_arch = dict(dest='--proposal_archive', type=Path, help='Path of the proposal archive table in JSON format')
investor_arch = dict(dest='--investor_archive', type=Path, help='Path of the investor archive table in JSON format')
allocated = dict(dest='--path', type=Path, help='Path of the exported file')
overwrite = dict(dest='-y', action='store_true', help='Automatically overwrite table data')
smp = dict(dest=('-s', '--smp'), type=int, help='The smp limit in CPU Hours', default=0)
mpi = dict(dest=('-m', '--mpi'), type=int, help='The mpi limit in CPU Hours', default=0)
gpu = dict(dest=('-g', '--gpu'), type=int, help='The gpu limit in CPU Hours', default=0)
htc = dict(dest=('-c', '--htc'), type=int, help='The htc limit in CPU Hours', default=0)
inv_id = dict(dest='--id', help='The investment proposal id')


class CLIParser(ArgumentParser):
    """Parser for command line arguments"""

    def __init__(self) -> None:
        super().__init__()
        self.subparsers = self.add_subparsers(parser_class=ArgumentParser)

        # Subparsers for account management and info

        parser_info = self.subparsers.add_parser('info')
        parser_info.set_defaults(function=functions.info)
        self._add_args_to_parser(parser_info, account)

        parser_usage = self.subparsers.add_parser('usage')
        parser_usage.set_defaults(function=functions.usage)
        self._add_args_to_parser(parser_usage, account)

        parser_reset_raw_usage = self.subparsers.add_parser('reset_raw_usage')
        parser_reset_raw_usage.set_defaults(function='account.reset_raw_usage')
        self._add_args_to_parser(parser_reset_raw_usage, account)

        parser_find_unlocked = self.subparsers.add_parser('find_unlocked')
        parser_find_unlocked.set_defaults(function=functions.find_unlocked)

        lock_acct = partial(functions.set_account_lock, lock_state=True, notify=True)
        parser_lock_with_notification = self.subparsers.add_parser('lock_with_notification')
        parser_lock_with_notification.set_defaults(function=lock_acct)
        self._add_args_to_parser(parser_lock_with_notification, account)

        unlock_acct = partial(functions.set_account_lock, lock_state=False, notify=False)
        parser_release_hold = self.subparsers.add_parser('release_hold')
        parser_release_hold.set_defaults(function=unlock_acct)
        self._add_args_to_parser(parser_release_hold, account)

        parser_check_proposal_end_date = self.subparsers.add_parser('check_proposal_end_date')
        parser_check_proposal_end_date.set_defaults(function=functions.alert_account)
        self._add_args_to_parser(parser_check_proposal_end_date, account)

        # Subparsers for adding and modifying general service unit allocations

        parser_insert = self.subparsers.add_parser('insert', help='Add a proposal to a user for the first time.')
        parser_insert.set_defaults(function=functions.insert)
        self._add_args_to_parser(parser_insert, prop_type, account, smp, mpi, gpu, htc)

        parser_add = self.subparsers.add_parser('add',
                                                help='Add SUs to an existing user proposal on top of current values.')
        parser_add.set_defaults(function=functions.add)
        self._add_args_to_parser(parser_add, account, smp, mpi, gpu, htc)

        parser_change = self.subparsers.add_parser('modify', help="Update the properties of a given account/proposal")
        parser_change.set_defaults(function=functions.modify)
        self._add_args_to_parser(parser_change, account, smp, mpi, gpu, htc)

        # Subparsers for adding and modifying investment accounts

        parser_investor = self.subparsers.add_parser('investor', help='Add an investment proposal to a given user')
        parser_investor.set_defaults(function=functions.investor)
        self._add_args_to_parser(parser_investor, account, sus)

        parser_investor_modify = self.subparsers.add_parser('investor_modify')
        parser_investor_modify.set_defaults(function=functions.investor_modify)
        self._add_args_to_parser(parser_investor, inv_id, sus)

        parser_renewal = self.subparsers.add_parser('renewal', help='Like modify but rolls over active investments')
        parser_renewal.set_defaults(function='account.renewal')
        self._add_args_to_parser(parser_renewal, account, smp, mpi, gpu, htc)

        parser_withdraw = self.subparsers.add_parser('withdraw')
        parser_withdraw.set_defaults(function=functions.withdraw)
        self._add_args_to_parser(parser_withdraw, account, sus)

    @staticmethod
    def _add_args_to_parser(parser: ArgumentParser, *arg_definitions: dict) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
            *arg_definitions: Dictionary with arguments for ``parser.add_argument``
        """

        for arg_def in arg_definitions:
            arg_def = arg_def.copy()
            parser.add_argument(**arg_def)

    def execute(self, *args, **kwargs) -> None:
        """Entry point for running the command line parser

        Parse command line arguments and evaluate the corresponding function
        """

        cli_kwargs = vars(self.parse_args(*args, **kwargs))  # Get parsed arguments as a dictionary
        cli_kwargs = {k.lstrip('-'): v for k, v in cli_kwargs.items()}
        cli_kwargs.pop('function')(**cli_kwargs)
