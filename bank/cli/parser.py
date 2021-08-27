"""Command line parsing for the ``bank`` package"""

from argparse import ArgumentParser
from pathlib import Path

from bank.dao import Account, Bank
from . import interface

# Reusable definitions for command line arguments
account = dict(flags='--account', type=Account, help='The associated slurm account')
prop_type = dict(flags='--type', type=str, help='The proposal type: proposal or class')
date = dict(flags='--date', help='The proposal start date (e.g 12/01/19)')
sus = dict(flags='--sus', type=int, help='The number of SUs you want to insert')

proposal = dict(flags='--proposal', type=Path, help='Path of the proposal table in JSON format')
investor = dict(flags='--investor', type=Path, help='Path of the investor table in JSON format')
proposal_arch = dict(flags='--proposal_archive', type=Path, help='Path of the proposal archive table in JSON format')
investor_arch = dict(flags='--investor_archive', type=Path, help='Path of the investor archive table in JSON format')
allocated = dict(flags='--path', type=Path, help='Path of the exported file')
overwrite = dict(flags='-y', action='store_true', help='Automatically overwrite table data')

smp = dict(flags=('-s', '--smp'), type=int, help='The smp limit in CPU Hours', default=0)
mpi = dict(flags=('-m', '--mpi'), type=int, help='The mpi limit in CPU Hours', default=0)
gpu = dict(flags=('-g', '--gpu'), type=int, help='The gpu limit in CPU Hours', default=0)
htc = dict(flags=('-c', '--htc'), type=int, help='The htc limit in CPU Hours', default=0)
inv_id = dict(flags='--id', help='The investment proposal id')


class CLIParser(ArgumentParser):
    """Parser for command line arguments"""

    def __init__(self) -> None:
        super().__init__()
        self.subparsers = self.add_subparsers(parser_class=ArgumentParser)

        parser_insert = self.subparsers.add_parser('insert', help='Insert for the first time.')
        parser_insert.set_defaults(function=Bank.insert)
        self.add_args_to_parser(parser_insert, prop_type, account, smp, mpi, gpu, htc)

        parser_modify = self.subparsers.add_parser('modify', help='Change to new limits, update proposal date')
        parser_modify.set_defaults()
        self.add_args_to_parser(parser_modify, account, smp, mpi, gpu, htc)

        parser_add = self.subparsers.add_parser('add', help='Add SUs on top of current values')
        parser_add.set_defaults()
        self.add_args_to_parser(parser_add, account, smp, mpi, gpu, htc)

        parser_change = self.subparsers.add_parser('change', help="Change to new limits, don't change proposal date")
        parser_change.set_defaults()
        self.add_args_to_parser(parser_change, account, smp, mpi, gpu, htc)

        parser_renewal = self.subparsers.add_parser('renewal', help='Like modify but rolls over active investments')
        parser_renewal.set_defaults(function=Bank.renewal)
        self.add_args_to_parser(parser_renewal, account, smp, mpi, gpu, htc)

        parser_date = self.subparsers.add_parser('date')
        parser_date.set_defaults()
        self.add_args_to_parser(parser_date, account, date)

        parser_date_investment = self.subparsers.add_parser('date_investment')
        parser_date_investment.set_defaults()
        self.add_args_to_parser(parser_date_investment, account, date, inv_id)

        parser_investor = self.subparsers.add_parser('investor')
        parser_investor.set_defaults(function=Bank.investor)
        self.add_args_to_parser(parser_investor, account, sus)

        parser_withdraw = self.subparsers.add_parser('withdraw')
        parser_withdraw.set_defaults(function=Bank.withdraw)
        self.add_args_to_parser(parser_withdraw, account, sus)

        parser_info = self.subparsers.add_parser('info')
        parser_info.set_defaults(function=interface.info)
        self.add_args_to_parser(parser_info, account)

        parser_usage = self.subparsers.add_parser('usage')
        parser_usage.set_defaults(function=Bank.usage)
        self.add_args_to_parser(parser_usage, account)

        parser_check_sus_limit = self.subparsers.add_parser('check_sus_limit')
        parser_check_sus_limit.set_defaults()
        self.add_args_to_parser(parser_check_sus_limit, account)

        parser_check_proposal_end_date = self.subparsers.add_parser('check_proposal_end_date')
        parser_check_proposal_end_date.set_defaults()
        self.add_args_to_parser(parser_check_proposal_end_date, account)

        parser_check_proposal_violations = self.subparsers.add_parser('check_proposal_violations')
        parser_check_proposal_violations.set_defaults(function=Bank.check_proposal_violations)

        parser_get_sus = self.subparsers.add_parser('get_sus')
        parser_get_sus.set_defaults(function=interface.get_sus)
        self.add_args_to_parser(parser_get_sus, account)

        parser_dump = self.subparsers.add_parser('dump')
        parser_dump.set_defaults()
        self.add_args_to_parser(parser_dump, proposal, investor, proposal_arch, investor_arch)

        parser_import_proposal = self.subparsers.add_parser('import_proposal')
        parser_import_proposal.set_defaults(function=Bank.import_proposal)
        self.add_args_to_parser(parser_import_proposal, proposal, overwrite)

        parser_import_investor = self.subparsers.add_parser('import_investor')
        parser_import_investor.set_defaults(function=Bank.import_investor)
        self.add_args_to_parser(parser_import_investor, investor, overwrite)

        parser_release_hold = self.subparsers.add_parser('release_hold')
        parser_release_hold.set_defaults(function=Bank.release_hold)
        self.add_args_to_parser(parser_release_hold, account)

        parser_alloc_sus = self.subparsers.add_parser('alloc_sus')
        parser_alloc_sus.set_defaults(function=interface.alloc_sus)
        self.add_args_to_parser(parser_alloc_sus, allocated)

        parser_reset_raw_usage = self.subparsers.add_parser('reset_raw_usage')
        parser_reset_raw_usage.set_defaults(function=Bank.reset_raw_usage)
        self.add_args_to_parser(parser_reset_raw_usage, account)

        parser_find_unlocked = self.subparsers.add_parser('find_unlocked')
        parser_find_unlocked.set_defaults(function=interface.find_unlocked)

        parser_lock_with_notification = self.subparsers.add_parser('lock_with_notification')
        parser_lock_with_notification.set_defaults(function=Bank.lock_with_notification)
        self.add_args_to_parser(parser_lock_with_notification, account)

    @staticmethod
    def add_args_to_parser(parser: ArgumentParser, *arg_definitions: dict, required: bool = False) -> None:
        """Add argument definitions to the command line parser

        Args:
            parser: The parser to add arguments to
            *arg_definitions: Dictionary with arguments for ``parser.add_argument``
            required: If the given arguments should be required
        """

        for arg_def in arg_definitions:
            arg_def = arg_def.copy()
            flags = arg_def.pop('flags')
            if isinstance(flags, str):
                parser.add_argument(flags, **arg_def, required=required)

            else:
                parser.add_argument(*flags, **arg_def, required=required)

    def execute(self) -> None:
        """Entry point for running the command line parser

        Parse command line arguments and evaluate the corresponding function
        """

        parsed_args = vars(self.parse_args())
        parsed_args.pop('function')(parsed_args)
