from unittest import TestCase
from unittest.mock import patch, call

from bank import dao
from bank.cli import CLIParser
from bank.settings import app_settings

TEST_ACCOUNT = 'sam'


class DynamicallyAddedClusterArguments(TestCase):
    """Test that selected subparsers have an argument for each cluster defined in the application settings"""

    subparser_names = ['insert', 'add', 'modify', 'renewal']

    def runTest(self) -> None:
        subparsers = CLIParser().subparsers
        clusters = set(app_settings.clusters)

        for subparser_name in self.subparser_names:
            parser = subparsers.choices[subparser_name]
            args = {a.dest.lstrip('--') for a in parser._actions}
            self.assertTrue(clusters.issubset(args), f'Parser {subparser_name} is missing arguments: {clusters - args}')


# Todo: Implement tests for:
#  usage
#  reset_raw_usage
#  find_unlocked
#  lock_with_notification
#  release_hold
#  check_proposal_end_date
#  insert
#  add
#  modify
#  investor
#  investor_modify
#  renewal
#  withdraw

class Info(TestCase):
    """Tests for the ``info`` subparser"""

    @patch('builtins.print')
    def runTest(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_usage_info`` function"""

        dao.Account(TEST_ACCOUNT).print_usage_info()
        CLIParser().execute(['info', TEST_ACCOUNT])
        self.assertEqual(mocked_print.mock_calls[0], mocked_print.mock_calls[1])


class Usage(TestCase):
    """Tests for the ``usage`` subparser"""

    def test_usage_fails_with_no_proposal(self) -> None:
        """
        run python crc_bank.py usage sam
        [ "$status" -eq 1 ]
        """

    def test_usage_works(self) -> None:
        """
        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        run python crc_bank.py usage sam
        [ "$status" -eq 0 ]
        [ $(echo $output | grep -c "Aggregate") -gt 0 ]
        [ $(echo $output | grep -c "Investment") -eq 0 ]
       """

    def test_usage_with_investment_works(self) -> None:
        """
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        run python crc_bank.py usage sam
        [ "$status" -eq 0 ]
        [ $(echo $output | grep -c "Aggregate") -gt 0 ]
        [ $(echo $output | grep -c "Investment") -gt 0 ]
        """


class Withdraw(TestCase):
    """Tests for the ``withdraw`` subparser"""

    def test_withdraw_works(self) -> None:
        """
        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        # withdraw from investment
        run python crc_bank.py withdraw sam 8000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # investor table should have rollover SUs
        [ $(grep -c '"count": 1' investor.json) -eq 1 ]
        [ $(grep -c '"service_units": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"rollover_sus": 0' investor.json) -eq 1 ]
        [ $(grep -c '"current_sus": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"withdrawn_sus": 10000' investor.json) -eq 1 ]
        """


class Modify(TestCase):
    """Tests for the ``modify`` subparser"""

    def test_modify_updates_SUs(self) -> None:
        """
         # insert proposal should work
         run python crc_bank.py insert proposal sam --smp=10000
         [ "$status" -eq 0 ]
 
         # modify the proposal date to 7 days prior
         run python crc_bank.py date sam $(date -d "-7 days" +%m/%d/%y)
 
         # dump the tables to JSON should work
         run python crc_bank.py dump proposal.json investor.json proposal_archive.json investor_archive.json
         [ "$status" -eq 0 ]
 
         # proposal should have 1 mpi entry with 10000 SUs
         [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
         [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]
         [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
         [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
         [ $(grep -c '"mpi": 0' proposal.json) -eq 1 ]
         [ $(grep -c "\"start_date\": \"$(date -d '-7 days' +%F)\"" proposal.json) -eq 1 ]
 
         # modify proposal should work
         run python crc_bank.py modify sam --mpi=10000
         [ "$status" -eq 0 ]
 
         # dump the tables to JSON should work
         run rm proposal.json investor.json proposal_archive.json investor_archive.json
         run python crc_bank.py dump proposal.json investor.json proposal_archive.json investor_archive.json
         [ "$status" -eq 0 ]
 
         # proposal should have 1 mpi entry with 10000 SUs
         [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
         [ $(grep -c '"smp": 0' proposal.json) -eq 1 ]
         [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
         [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
         [ $(grep -c '"mpi": 10000' proposal.json) -eq 1 ]
         [ $(grep -c "\"start_date\": \"$(date +%F)\"" proposal.json) -eq 1 ]
         """


class Insert(TestCase):
    """Tests for the ``insert`` subparser"""

    def insert_works(self) -> None:
        """    
        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # info should work and print something
        run python crc_bank.py info sam
        [ "$status" -eq 0 ]
        [ "$output" != "" ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal should have 1 smp entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]
        [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"mpi": 0' proposal.json) -eq 1 ]
        [ $(grep -c "\"start_date\": \"$(date +%F)\"" proposal.json) -eq 1 ]

        # all other tables should be empty
        [ $(grep -c '{}' proposal_archive.json) -eq 1 ]
        [ $(grep -c '{}' investor.json) -eq 1 ]
        [ $(grep -c '{}' investor_archive.json) -eq 1 ]
        """


class Renewal(TestCase):
    """Tests for the ``renewal`` subparser"""

    def renewal_with_rollover(self) -> None:
        """    
        # Check raw_usage
        raw_usage=$(get_raw_usage sam)
        [ $raw_usage -lt 100 ]

        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        # modify the proposal date to 1 year
        run python crc_bank.py date_investment sam $(date -d "-365 days" +%m/%d/%y) 1
        [ "$status" -eq 0 ]

        # proposal renewal should work
        run python crc_bank.py renewal sam --smp=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal table should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]

        # proposal archive should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal_archive.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal_archive.json) -eq 1 ]

        # investor table should have rollover SUs
        [ $(grep -c '"count": 1' investor.json) -eq 1 ]
        [ $(grep -c '"service_units": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"current_sus": 2000' investor.json) -eq 1 ]
        [ $(grep -c '"withdrawn_sus": 4000' investor.json) -eq 1 ]
        [ $(grep -c '"rollover_sus": 1000' investor.json) -eq 1 ]
        """

    def double_renewal_with_rollover(self) -> None:
        """
        # Check raw_usage
        raw_usage=$(get_raw_usage sam)
        [ $raw_usage -lt 100 ]

        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        # modify the proposal date to 1 year
        run python crc_bank.py date_investment sam $(date -d "-365 days" +%m/%d/%y) 1
        [ "$status" -eq 0 ]

        # proposal renewal should work
        run python crc_bank.py renewal sam --smp=10000
        [ "$status" -eq 0 ]

        # modify the proposal date to 2 years (might fail on leap years?)
        run python crc_bank.py date_investment sam $(date -d "-730 days" +%m/%d/%y) 1
        [ "$status" -eq 0 ]

        # proposal renewal should work
        run python crc_bank.py renewal sam --smp=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal table should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]

        # proposal archive should have 2 entry with 10000 SUs
        [ $(grep -c '"count": 2' proposal_archive.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal_archive.json) -eq 2 ]

        # investor table should have rollover SUs
        [ $(grep -c '"count": 1' investor.json) -eq 1 ]
        [ $(grep -c '"service_units": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"rollover_sus": 1000' investor.json) -eq 1 ]
        [ $(grep -c '"current_sus": 2000' investor.json) -eq 1 ]
        [ $(grep -c '"withdrawn_sus": 6000' investor.json) -eq 1 ]
        """

    def after_withdraw_renew_twice_should_archive_investment(self) -> None:
        """    
        # Check raw_usage
        raw_usage=$(get_raw_usage sam)
        [ $raw_usage -lt 100 ]

        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        # withdraw all investor SUs
        run python crc_bank.py withdraw sam 8000
        [ "$status" -eq 0 ]

        # proposal renewal should work
        run python crc_bank.py renewal sam --smp=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal table should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]

        # proposal archive should have 2 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal_archive.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal_archive.json) -eq 1 ]

        # investor table should have rollover SUs
        [ $(grep -c '"count": 1' investor.json) -eq 1 ]
        [ $(grep -c '"service_units": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"rollover_sus": 5000' investor.json) -eq 1 ]
        [ $(grep -c '"current_sus": 0' investor.json) -eq 1 ]
        [ $(grep -c '"withdrawn_sus": 10000' investor.json) -eq 1 ]

        run rm proposal.json investor.json proposal_archive.json investor_archive.json

        # proposal renewal should work
        run python crc_bank.py renewal sam --smp=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal table should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]

        # proposal archive should have 2 entry with 10000 SUs
        [ $(grep -c '"count": 2' proposal_archive.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal_archive.json) -eq 2 ]

        # investor table should be empty
        [ $(wc -l investor.json | awk '{print $1}') -eq 1 ]
        [ $(grep -c '{}' investor.json) -eq 1 ]

        # investor archive should have one investment
        [ $(grep -c '"count": 1' investor_archive.json) -eq 1 ]
        """


class Investor(TestCase):
    """Tests for the ``investor`` subparser"""

    def investor_fails_with_no_proposal(self) -> None:
        """
        # insert investment should not work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 1 ]
        """

    def investor_works(self) -> None:
        """
        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # insert investment should work
        run python crc_bank.py investor sam 10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal table should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]
        [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"mpi": 0' proposal.json) -eq 1 ]

        # investor table should not have rollover SUs
        [ $(grep -c '"count": 1' investor.json) -eq 1 ]
        [ $(grep -c '"service_units": 10000' investor.json) -eq 1 ]
        [ $(grep -c '"current_sus": 2000' investor.json) -eq 1 ]
        [ $(grep -c '"withdrawn_sus": 2000' investor.json) -eq 1 ]
        [ $(grep -c '"rollover_sus": 0' investor.json) -eq 1 ]
        """


class Add(TestCase):
    """Tests for the ``add`` subparser"""

    def add_updates_sus(self) -> None:
        """
        # insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # add proposal should work
        run python crc_bank.py add sam --mpi=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal should have 1 entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 10000' proposal.json) -eq 1 ]
        [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"mpi": 10000' proposal.json) -eq 1 ]
        """


class Change(TestCase):
    """Tests for the ``change`` subparser"""

    def change_updates_SUs(self) -> None:
        """"# insert proposal should work
        run python crc_bank.py insert proposal sam --smp=10000
        [ "$status" -eq 0 ]

        # modify the proposal date to 7 days prior
        run python crc_bank.py date sam $(date -d "-7 days" +%m/%d/%y)

        # modify proposal should work
        run python crc_bank.py change sam --mpi=10000
        [ "$status" -eq 0 ]

        # dump the tables to JSON should work
        run python crc_bank.py dump proposal.json investor.json \
            proposal_archive.json investor_archive.json
        [ "$status" -eq 0 ]

        # proposal should have 1 mpi entry with 10000 SUs
        [ $(grep -c '"count": 1' proposal.json) -eq 1 ]
        [ $(grep -c '"smp": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"gpu": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"htc": 0' proposal.json) -eq 1 ]
        [ $(grep -c '"mpi": 10000' proposal.json) -eq 1 ]
        [ $(grep -c "\"start_date\": \"$(date -d '-7 days' +%F)\"" proposal.json) -eq 1 ]
        """
