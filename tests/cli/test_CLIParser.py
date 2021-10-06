from unittest import TestCase
from unittest.mock import patch

from bank import dao
from bank.cli import CLIParser
from bank.settings import app_settings
from bank.system import SlurmAccount

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


class Info(TestCase):
    """Tests for the ``info`` subparser"""

    @patch('builtins.print')
    def runTest(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_allocation_info`` function"""

        dao.Account(TEST_ACCOUNT).print_allocation_info()
        CLIParser().execute(['info', TEST_ACCOUNT])
        self.assertEqual(mocked_print.mock_calls[0], mocked_print.mock_calls[1])


# Todo: These test can be extended to include an account with and without investments
class Usage(TestCase):
    """Tests for the ``usage`` subparser"""

    @patch('builtins.print')
    def runTest(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_usage_info`` function"""

        dao.Account(TEST_ACCOUNT).print_usage_info()
        CLIParser().execute(['usage', TEST_ACCOUNT])
        self.assertEqual(mocked_print.mock_calls[0], mocked_print.mock_calls[1])


class ResetRawUsage(TestCase):
    """Tests for the ``reset_raw_usage`` subparser"""

    def setUp(self) -> None:
        """Assign a non zero amount of service units to the test user account"""

        self.slurm_account = SlurmAccount(TEST_ACCOUNT)
        self.slurm_account.set_raw_usage(10_000, *app_settings.clusters)

    def test_usage_is_reset(self) -> None:
        """Test the subparser successfully sets the raw account usage to zero"""

        CLIParser().execute(['reset_raw_usage', TEST_ACCOUNT])
        for cluster in app_settings.clusters:
            self.assertEqual(0, self.slurm_account.get_cluster_usage(cluster))


# Todo: test that a notification is sent when notify=True
class LockWithNotification(TestCase):
    """Tests for the ``lock_with_notification`` subparser"""

    def test_account_is_locked(self) -> None:
        """Test that an unlocked account becomes locked"""

        account = dao.Account(TEST_ACCOUNT)
        account.set_locked_state(False)
        CLIParser().execute(['lock_with_notification', TEST_ACCOUNT, 'notify=False'])
        self.assertTrue(account.get_locked_state())


class ReleaseHold(TestCase):
    """Tests for the ``release_hold`` subparser"""

    def test_account_is_unlocked(self) -> None:
        """Test that a locked account becomes unlocked"""

        account = dao.Account(TEST_ACCOUNT)
        account.set_locked_state(True)
        CLIParser().execute(['release_hold', TEST_ACCOUNT])
        self.assertFalse(account.get_locked_state())


# Todo: Implement tests for:
#  check_proposal_end_date
#  insert
#  add
#  modify
#  investor
#  investor_modify
#  renewal
#  withdraw

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
