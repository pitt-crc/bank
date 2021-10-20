from unittest import TestCase, skipIf
from unittest.mock import patch

from bank import dao, orm
from bank.cli import CLIParser
from bank.dao import Account, Bank
from bank.exceptions import MissingProposalError
from bank.settings import app_settings
from bank.system import RequireRoot

TEST_ACCOUNT = 'sam'

# Todo: Implement tests for:
#  check_proposal_end_date
#  investor_modify
#  renewal
#  withdraw

try:
    Account(app_settings.test_account)

except MissingProposalError:
    Bank().create_proposal(app_settings.test_account, 'PROPOSAL')


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
    def test_info_is_printed(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_allocation_info`` function"""

        dao.Account(TEST_ACCOUNT).print_allocation_info()
        CLIParser().execute(['info', TEST_ACCOUNT])
        self.assertEqual(mocked_print.mock_calls[0], mocked_print.mock_calls[1])


# Todo: These test can be extended to include an account with and without investments
class Usage(TestCase):
    """Tests for the ``usage`` subparser"""

    @patch('builtins.print')
    def test_usage_is_printed(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_usage_info`` function"""

        dao.Account(TEST_ACCOUNT).print_usage_info()
        CLIParser().execute(['usage', TEST_ACCOUNT])
        self.assertEqual(mocked_print.mock_calls[0], mocked_print.mock_calls[1])


# Todo: test that a notification is sent when notify=True
class LockWithNotification(TestCase):
    """Tests for the ``lock_with_notification`` subparser"""

    @skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
    def test_account_is_locked(self) -> None:
        """Test that an unlocked account becomes locked"""

        account = dao.Account(TEST_ACCOUNT)
        account.set_locked_state(False)
        CLIParser().execute(['lock_with_notification', TEST_ACCOUNT, 'notify=False'])
        self.assertTrue(account.get_locked_state())


class ReleaseHold(TestCase):
    """Tests for the ``release_hold`` subparser"""

    @skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
    def test_account_is_unlocked(self) -> None:
        """Test that a locked account becomes unlocked"""

        account = dao.Account(TEST_ACCOUNT)
        account.set_locked_state(True)
        CLIParser().execute(['release_hold', TEST_ACCOUNT])
        self.assertFalse(account.get_locked_state())


# Todo: Test what happens if we insert and a proposal already exists
class Insert(TestCase):
    """Tests for the ``insert`` subparser"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.first_cluster, *_ = app_settings.clusters
        cls.number_sus = 10_000
        CLIParser().execute(['insert', 'proposal', TEST_ACCOUNT, f'--{cls.first_cluster}={cls.number_sus}'])

    def test_proposal_is_created_for_cluster(self) -> None:
        """Test that a proposal has been created for the user account and cluster"""

        # Test service units have been allocated to the cluster specified to the CLI parser
        allocations = dao.Account(TEST_ACCOUNT).get_cluster_allocation()
        self.assertEqual(self.number_sus, allocations.pop(self.first_cluster))

        # Test all other clusters have zero service units
        for cluster, sus in allocations.items():
            self.assertEqual(0, sus, f'Cluster {cluster} should have zero service units. Got {sus}.')


class Add(TestCase):
    """Tests for the ``add`` subparser"""

    def test_sus_are_updated(self) -> None:
        """Test the allocated service units are incremented by a given amount"""

        account = dao.Account(TEST_ACCOUNT)
        test_cluster_name, *other_clusters = app_settings.clusters
        original_sus = account.get_cluster_allocation()

        sus_to_add = 100
        CLIParser().execute(['add', TEST_ACCOUNT, f'--{test_cluster_name}={sus_to_add}'])
        new_sus = account.get_cluster_allocation()

        self.assertEqual(new_sus[test_cluster_name], original_sus[test_cluster_name] + sus_to_add)
        for cluster in other_clusters:
            self.assertEqual(new_sus[cluster], original_sus[cluster])


class Modify(TestCase):
    """Tests for the ``modify`` subparser"""

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

    def test_modify_updates_SUs(self) -> None:
        """Test the command updates sus on the given cluster"""

        account = dao.Account(TEST_ACCOUNT)
        test_cluster = app_settings.clusters[0]
        account.set_cluster_allocation(**{test_cluster: 0})

        new_sus = 1_000
        CLIParser().execute(['modify', TEST_ACCOUNT, f'--{test_cluster}={new_sus}'])
        self.assertEqual(new_sus, account.get_cluster_allocation()[test_cluster])


class Investor(TestCase):
    """Tests for the ``investor`` subparser"""

    @classmethod
    def setUpClass(cls) -> None:
        """Delete any existing investments"""

        with orm.Session() as session:
            session.query(orm.Investor).filter_by(orm.Investor.account_name == TEST_ACCOUNT).delete()
            session.commit()

    def test_investment_is_created(self) -> None:
        """Test an investment is created with the correct number of sus"""

        num_sus = 15_000
        CLIParser().execute(['investor', TEST_ACCOUNT, num_sus])

        account = dao.Account(TEST_ACCOUNT)
        self.assertEqual(1, len(account.get_investment_sus()))

        inv_sus = next(iter(account.get_investment_sus().values()))
        self.assertEqual(num_sus, inv_sus)


class InvestorModify(TestCase):
    """Tests for the ``investor_modify`` subparser"""

    def test_modify_updates_SUs(self) -> None:
        """Test the command updates sus on the given investment"""

        account = dao.Account(TEST_ACCOUNT)
        inv_id, original_sus = next(iter(account.get_investment_sus().items()))

        new_sus = original_sus + 10
        CLIParser().execute(['investor_modify', inv_id, new_sus])
        self.assertEqual(new_sus, next(iter(account.get_investment_sus().values())))


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
