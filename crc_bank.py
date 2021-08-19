#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python
"""Command line interface for the ``bank`` package"""

import argparse

from bank.dao import Bank

# Reusable definitions of command line arguments and their help messages
account = dict(name_or_flags='--account', help='The associated slurm account')
prop_type = dict(name_or_flags='--type', help='The proposal type: proposal or class')
date = dict(name_or_flags='--date', help='The proposal start date (e.g 12/01/19)')
sus = dict(name_or_flags='--sus', help='The number of SUs you want to insert')

proposal = dict(name_or_flags='--proposal', help='Path for the proposal table in JSON format')
investor = dict(name_or_flags='--investor', help='Path for the investor table in JSON format')
proposal_archive = dict(name_or_flags='--proposal_archive', help='Path for the proposal archival table in JSON format')
investor_archive = dict(name_or_flags='--investor_archive', help='Path for the investor archival table in JSON format')
overwrite = dict(name_or_flags='-y', action='store_true', help='Automatically overwrite table data')

smp = dict(name_or_flags='-s', help='The smp limit in CPU Hours', default=0, required=False)
mpi = dict(name_or_flags='-m', help='The mpi limit in CPU Hours', default=0, required=False)
gpu = dict(name_or_flags='-g', help='The gpu limit in CPU Hours', default=0, required=False)
htc = dict(name_or_flags='-c', help='The htc limit in CPU Hours', default=0, required=False)
inv_id = dict(name_or_flags='--id')

# Create a dedicated subparser for each function we want to expose on the
# command line and add the necessary arguments
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

parser_insert = subparsers.add_parser('insert', help='Insert for the first time.')
parser_insert.set_defaults(function=Bank.insert)
parser_insert.add_argument(**prop_type)
parser_insert.add_argument(**account)
parser_insert.add_argument(**smp)
parser_insert.add_argument(**mpi)
parser_insert.add_argument(**gpu)
parser_insert.add_argument(**htc)

parser_modify = subparsers.add_parser('modify', help='Change to new limits, update proposal date')
parser_modify.set_defaults(function=Bank.modify)
parser_modify.add_argument(**account)
parser_modify.add_argument(**smp)
parser_modify.add_argument(**mpi)
parser_modify.add_argument(**gpu)
parser_modify.add_argument(**htc)

parser_add = subparsers.add_parser('add', help='Add SUs on top of current values')
parser_add.set_defaults(function=Bank.add)
parser_add.add_argument(**account)
parser_add.add_argument(**smp)
parser_add.add_argument(**mpi)
parser_add.add_argument(**gpu)
parser_add.add_argument(**htc)

parser_change = subparsers.add_parser('change', help="Change to new limits, don't change proposal date")
parser_change.set_defaults(function=Bank.change)
parser_change.add_argument(**account)
parser_change.add_argument(**smp)
parser_change.add_argument(**mpi)
parser_change.add_argument(**gpu)
parser_change.add_argument(**htc)

parser_renewal = subparsers.add_parser('renewal', help='Similar to modify, except rolls over active investments')
parser_renewal.set_defaults(function=Bank.renewal)
parser_renewal.add_argument(**account)
parser_renewal.add_argument(**smp)
parser_renewal.add_argument(**mpi)
parser_renewal.add_argument(**gpu)
parser_renewal.add_argument(**htc)

parser_date = subparsers.add_parser('date')
parser_date.set_defaults(function=Bank.date)
parser_date.add_argument(**account)
parser_date.add_argument(**date)

parser_date_investment = subparsers.add_parser('date_investment')
parser_date_investment.set_defaults(function=Bank.date_investment)
parser_date_investment.add_argument(**account)
parser_date_investment.add_argument(**date)
parser_date_investment.add_argument(**inv_id)

parser_investor = subparsers.add_parser('investor')
parser_investor.set_defaults(function=Bank.investor)
parser_investor.add_argument(**account)
parser_investor.add_argument(**sus)

parser_withdraw = subparsers.add_parser('withdraw')
parser_withdraw.set_defaults(function=Bank.withdraw)
parser_withdraw.add_argument(**account)
parser_withdraw.add_argument(**sus)

parser_info = subparsers.add_parser('info')
parser_info.set_defaults(function=Bank.info)
parser_info.add_argument(**account)

parser_usage = subparsers.add_parser('usage')
parser_usage.set_defaults(function=Bank.usage)
parser_usage.add_argument(**account)

parser_check_sus_limit = subparsers.add_parser('check_sus_limit')
parser_check_sus_limit.set_defaults(function=Bank.check_sus_limit)
parser_check_sus_limit.add_argument(**account)

parser_check_proposal_end_date = subparsers.add_parser('check_proposal_end_date')
parser_check_proposal_end_date.set_defaults(function=Bank.check_proposal_end_date)
parser_check_proposal_end_date.add_argument(**account)

parser_check_proposal_violations = subparsers.add_parser('check_proposal_violations')
parser_check_proposal_violations.set_defaults(function=Bank.check_proposal_violations)

parser_get_sus = subparsers.add_parser('get_sus')
parser_get_sus.set_defaults(function=Bank.get_sus)
parser_get_sus.add_argument(**account)

parser_dump = subparsers.add_parser('dump')
parser_dump.set_defaults(function=Bank.dump)
parser_dump.add_argument(**proposal)
parser_dump.add_argument(**investor)
parser_dump.add_argument(**proposal_archive)
parser_dump.add_argument(**investor_archive)

parser_import_proposal = subparsers.add_parser('import_proposal')
parser_import_proposal.set_defaults(function=Bank.import_proposal)
parser_import_proposal.add_argument(**proposal)
parser_import_proposal.add_argument(**overwrite)

parser_import_investor = subparsers.add_parser('import_investor')
parser_import_investor.set_defaults(function=Bank.import_investor)
parser_import_investor.add_argument(**investor)
parser_import_investor.add_argument(**overwrite)

parser_release_hold = subparsers.add_parser('release_hold')
parser_release_hold.set_defaults(function=Bank.release_hold)
parser_release_hold.add_argument(**account)

parser_alloc_sus = subparsers.add_parser('alloc_sus')
parser_alloc_sus.set_defaults(function=Bank.alloc_sus)

parser_reset_raw_usage = subparsers.add_parser('reset_raw_usage')
parser_reset_raw_usage.set_defaults(function=Bank.reset_raw_usage)
parser_reset_raw_usage.add_argument(**account)

parser_find_unlocked = subparsers.add_parser('find_unlocked')
parser_find_unlocked.set_defaults(function=Bank.find_unlocked)

parser_lock_with_notification = subparsers.add_parser('lock_with_notification')
parser_lock_with_notification.set_defaults(function=Bank.lock_with_notification)
parser_lock_with_notification.add_argument(**account)
