from copy import copy
from datetime import timedelta
from unittest import TestCase, skipIf
from unittest.mock import patch

from bank import dao, orm
from bank.cli import CLIParser
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from bank.settings import app_settings
from bank.system import RequireRoot
from tests.testing_utils import InvestorSetup, ProtectLockState, ProposalSetup


# Todo: Implement tests for:
#  check_proposal_end_date
#  investor_modify
#  renewal
#  withdraw


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


class Info(InvestorSetup, TestCase):
    """Tests for the ``info`` subparser"""

    @patch('builtins.print')
    def test_info_is_printed(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches output from the DAO layer"""

        # Record output to stdout by the DAO
        dao.Account(app_settings.test_account).print_allocation_info()
        expected_prints = copy(mocked_print.mock_calls)

        # Record stdout from CLI and compare against previous result
        CLIParser().execute(['info', app_settings.test_account])
        cli_prints = mocked_print.mock_calls[len(expected_prints):]
        self.assertEqual(expected_prints, cli_prints)

    def test_error_on_missing_account(self) -> None:
        """Test a ``MissingProposalError`` error is raised if the account does not exist"""

        with self.assertRaises(MissingProposalError):
            CLIParser().execute(['info', 'fake_account'])


class Usage(InvestorSetup, TestCase):
    """Tests for the ``usage`` subparser"""

    @patch('builtins.print')
    def test_usage_is_printed(self, mocked_print) -> None:
        """Test the output from the subparser to stdout matches matches the ``print_usage_info`` function"""

        dao.Account(app_settings.test_account).print_usage_info()
        expected_prints = copy(mocked_print.mock_calls)

        CLIParser().execute(['usage', app_settings.test_account])
        cli_prints = mocked_print.mock_calls[len(expected_prints):]
        self.assertEqual(expected_prints, cli_prints)

    def test_error_on_missing_account(self) -> None:
        """Test a ``MissingProposalError`` error is raised if the account does not exist"""

        with self.assertRaises(MissingProposalError):
            CLIParser().execute(['usage', 'fake_account'])


@skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
class LockWithNotification(ProtectLockState, TestCase):
    """Tests for the ``lock_with_notification`` subparser"""

    def test_account_is_locked(self) -> None:
        """Test that an unlocked account becomes locked"""

        account = dao.Account(app_settings.test_account)
        account.set_locked_state(False)
        CLIParser().execute(['lock_with_notification', app_settings.test_account, 'notify=False'])
        self.assertTrue(account.get_locked_state())


@skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
class ReleaseHold(ProtectLockState, TestCase):
    """Tests for the ``release_hold`` subparser"""

    def test_account_is_unlocked(self) -> None:
        """Test that a locked account becomes unlocked"""

        account = dao.Account(app_settings.test_account)
        account.set_locked_state(True)
        CLIParser().execute(['release_hold', app_settings.test_account])
        self.assertFalse(account.get_locked_state())


class Insert(TestCase):
    """Tests for the ``insert`` subparser"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

    def test_proposal_is_created(self) -> None:
        """Test that a proposal has been created for the user account and cluster"""

        number_of_sus = 5000
        CLIParser().execute(['insert', 'proposal', app_settings.test_account, f'--{app_settings.test_cluster}={number_of_sus}'])

        # Test service units have been allocated to the cluster specified to the CLI parser
        allocations = dao.Account(app_settings.test_account).get_proposal_info()
        self.assertEqual(number_of_sus, allocations.pop(app_settings.test_cluster))

        # Test all other clusters have zero service units
        for cluster, sus in allocations.items():
            self.assertEqual(0, sus, f'Cluster {cluster} should have zero service units. Got {sus}.')

    def test_error_if_already_exists(self) -> None:
        """Test a ``ProposalExistsError`` error is raised if the proposal already exists"""

        dao.Account(app_settings.test_account).create_proposal(**{app_settings.test_cluster: 1000})
        with self.assertRaises(ProposalExistsError):
            CLIParser().execute(['insert', 'proposal', app_settings.test_account, f'--{app_settings.test_cluster}=1000'])

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            CLIParser().execute(['insert', 'proposal', app_settings.test_account, f'--{app_settings.test_cluster}=-1'])

    def test_error_on_invalid_proposal_type(self) -> None:
        """Test an error is raised for invalid proposal types"""

        with self.assertRaises(ValueError):
            CLIParser().execute(['insert', 'invalidValue', app_settings.test_account])


class Add(ProposalSetup, TestCase):
    """Tests for the ``add`` subparser"""

    def test_sus_are_updated(self) -> None:
        """Test the allocated service units are incremented by a given amount"""

        account = dao.Account(app_settings.test_account)
        original_sus = account.get_proposal_info()[app_settings.test_cluster]

        sus_to_add = 100
        CLIParser().execute(['add', app_settings.test_account, f'--{app_settings.test_cluster}={sus_to_add}'])
        new_sus = account.get_proposal_info()[app_settings.test_cluster]

        self.assertEqual(original_sus + sus_to_add, new_sus)

    def test_error_on_invalid_cluster(self) -> None:
        """Test an error is raised when passed an invalid cluster name"""

        with self.assertRaises(ValueError):
            CLIParser().execute(['add', app_settings.test_account, '--fake_cluster=1000'])

    def test_error_on_missing_account(self) -> None:
        """Test an error is raised when passed an account with a missing proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            CLIParser().execute(['add', app_settings.test_account, f'--{app_settings.test_cluster}=1000'])


class Modify(ProposalSetup, TestCase):
    """Tests for the ``modify`` subparser"""

    def test_date_is_updated(self) -> None:
        """Test the command updates the date on the proposal"""

        account = dao.Account(app_settings.test_account)
        old_date = account.get_proposal_info()['start_date']
        new_date = (old_date - timedelta(days=1)).strftime(app_settings.date_format)

        CLIParser().execute(['modify', app_settings.test_account, f'--date={new_date}'])
        self.assertEqual(new_date, account.get_proposal_info()['start_date'])

    def test_service_units_are_updated(self) -> None:
        """Test the command updates sus on the given cluster"""

        # Set the existing allocation to zero
        account = dao.Account(app_settings.test_account)
        account.overwrite_allocation_sus(**{app_settings.test_cluster: 0})

        new_sus = 1_000
        CLIParser().execute(['modify', app_settings.test_account, f'--{app_settings.test_cluster}={new_sus}'])
        self.assertEqual(new_sus, account.get_proposal_info()[app_settings.test_cluster])

    def test_error_on_missing_account(self) -> None:
        """Test an error is raised when passed an account with a missing proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            CLIParser().execute(['modify', app_settings.test_account, f'--{app_settings.test_cluster}=1000'])


class Investor(TestCase):
    """Tests for the ``investor`` subparser"""

    @classmethod
    def setUpClass(cls) -> None:
        """Delete any existing investments"""

        with orm.Session() as session:
            session.query(orm.Investor).filter(orm.Investor.account_name == app_settings.test_account).delete()
            session.commit()

    def test_investment_is_created(self) -> None:
        """Test an investment is created with the correct number of sus"""

        num_sus = 15_000
        CLIParser().execute(['investor', app_settings.test_account, str(num_sus)])

        account = dao.Account(app_settings.test_account)
        self.assertEqual(1, len(account.get_investment_sus()))

        inv_sus = next(iter(account.get_investment_sus().values()))
        self.assertEqual(num_sus, inv_sus)


class InvestorModify(TestCase):
    """Tests for the ``investor_modify`` subparser"""

    def test_modify_updates_SUs(self) -> None:
        """Test the command updates sus on the given investment"""

        account = dao.Account(app_settings.test_account)
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
