from datetime import date, timedelta
from unittest import TestCase, skip
from unittest.mock import patch

import time_machine
from sqlalchemy import join, select

from bank import settings
from bank.account_logic import AccountServices
from bank.orm import Account, Allocation, DBConnection, Proposal
from bank.system.slurm import SlurmAccount, Slurm
from tests._utils import active_proposal_query, active_investment_query, InvestmentSetup, ProposalSetup


class CalculatePercentage(TestCase):
    """Tests for the calculation of percentages"""

    def test_divide_by_zero(self) -> None:
        """Test dividing by zero returns zero"""

        self.assertEqual(0, AccountServices._calculate_percentage(100, 0))

    def test_divide_by_positive(self) -> None:
        """Test dividing by a positive number gives a percentage"""

        self.assertEqual(50, AccountServices._calculate_percentage(1, 2))


class AccountLocking(TestCase):
    """Test locking the account via the ``lock`` method"""

    def test_account_locked_on_cluster(self) -> None:
        """Test the account is locked on a given cluster"""

        slurm_account = SlurmAccount(settings.test_accounts[0])
        slurm_account.set_locked_state(False, settings.test_cluster)

        account_services = AccountServices(settings.test_accounts[0])
        account_services.lock(clusters=[settings.test_cluster])
        self.assertTrue(slurm_account.get_locked_state(settings.test_cluster))

    @patch.object(Slurm, "partition_names", lambda self: (settings.test_accounts[0],))
    def test_account_unlocked_on_investment_partition(self) -> None:
        """Test the account is locked on a given cluster"""

        slurm_account = SlurmAccount(settings.test_accounts[0])
        slurm_account.set_locked_state(False, settings.test_cluster)

        account_services = AccountServices(settings.test_accounts[0])
        account_services.lock(clusters=[settings.test_cluster])
        self.assertFalse(slurm_account.get_locked_state(settings.test_cluster))


class AccountUnlocking(TestCase):
    """Test unlocking the account"""

    def test_account_unlocked_on_cluster(self) -> None:
        """Test the account is unlocked on a given cluster"""

        slurm_account = SlurmAccount(settings.test_accounts[0])
        slurm_account.set_locked_state(True, settings.test_cluster)

        account_services = AccountServices(settings.test_accounts[0])
        account_services.unlock(clusters=[settings.test_cluster])
        self.assertFalse(slurm_account.get_locked_state(settings.test_cluster))


class BuildUsageTable(ProposalSetup, InvestmentSetup, TestCase):
    """Test _build_usage_table functionality for an individual account"""
    def setUp(self) -> None:
        """Instantiate an AccountServices and SlurmAccount object for the test account"""

        super().setUp()
        self.account = AccountServices(settings.test_accounts[0])
        self.slurm_account = SlurmAccount(settings.test_accounts[0])

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_table_built(self) -> None:
        """Test that the usage table is built properly"""

        table = self.account._build_usage_table()

        # TODO come up with one or more assertions to check the table output
        #self.assertTrue()


class GetActiveProposalEndDate(ProposalSetup, TestCase):
    """Tests for _get_active_proposal_end_date"""

    def setUp(self) -> None:
        """Instantiate an AccountServices object for the test account"""
        super().setUp()
        self.account = AccountServices(settings.test_accounts[0])

    def test_date_correct(self) -> None:
        """Test that the date is returned correctly in the expected format"""

        endDate = self.account._get_active_proposal_end_date()
        self.assertEqual(endDate, date.today() + timedelta(days=365))


class Insert(ProposalSetup, TestCase):
    """Test first time insertion of the account into the DB"""
    def setUp(self) -> None:
        """Instantiate an AccountServices and SlurmAccount object for the test account"""

        super().setUp()
        self.account = AccountServices(settings.test_accounts[0])
        self.slurm_account = SlurmAccount(settings.test_accounts[0])

    def test_account_inserted(self) -> None:
        """Test the account has an entry in the DB after insertion"""

        # Insert an entry into the database for an account with an existing SLURM account
        account_services = AccountServices(settings.test_accounts[0])
        account_services.insert()

        with DBConnection.session() as session:
            # Query the DB for the account
            account_query = select(Account).where(Account.name == self.account._account_name)
            account = session.execute(account_query).scalars().first()

            # The account entry should not be empty, and the name should match the name provided
            self.assertNotEmpty(account)
            self.assertEquals(account.name, settings.test_accounts[0])


@skip('This functionality hasn\'t been fully implemented yet.')
@patch('smtplib.SMTP.send_message')
class NotifyAccount(ProposalSetup, InvestmentSetup, TestCase):
    """Test for emails sent when locking accounts"""

    def setUp(self) -> None:
        super().setUp()

        self.account = AccountServices(settings.test_accounts[0])

        with DBConnection.session() as session:
            active_proposal = session.execute(active_proposal_query).scalars().first()
            self.proposal_end_date = active_proposal.end_date

    @patch('bank.system.SlurmAccount.set_locked_state')
    def test_email_sent_for_expired(self, mock_locked_state, mock_send_message) -> None:
        """Test an expiration email is sent if the account is is_expired"""

        with time_machine.travel(self.proposal_end_date + timedelta(days=100)):
            self.account.notify()

        # Make sure the account was notified
        mock_send_message.assert_called_once()
        sent_email = mock_send_message.call_args[0][0]
        self.assertEqual(f'The account for {self.account._account_name} has reached its end date', sent_email['subject'])

        # Make sure account was locked
        mock_locked_state.assert_called_once()
        lock_state = mock_locked_state.call_args.args[0]
        self.assertTrue(lock_state, 'Account was not locked')

    @patch.object(settings, "warning_days", (10,))
    def test_email_sent_for_warning_day(self, mock_send_message) -> None:
        """Test a warning email is sent if the account has reached an expiration warning limit"""

        # Note: ``time_machine.travel`` travels to just before the given point in time
        with time_machine.travel(self.proposal_end_date - timedelta(days=9)):
            self.account.notify()

        mock_send_message.assert_called_once()
        sent_email = mock_send_message.call_args[0][0]
        self.assertEqual(f'Your proposal expiry reminder for account: {self.account._account_name}', sent_email['subject'])

    @patch.object(settings, "notify_levels", (1,))  # Ensure a notification is sent after small usage percentage
    @patch.object(SlurmAccount, "get_total_usage", lambda self: 100)  # Ensure account usage is a reproducible value for testing
    def test_email_sent_for_percentage(self, mock_send_message) -> None:
        """Test a warning email is sent if the account exceeds a certain usage percentage"""

        self.account.notify()
        mock_send_message.assert_called_once()
        sent_email = mock_send_message.call_args[0][0]
        self.assertEqual(f'Your account {self.account._account_name} has exceeded a proposal threshold', sent_email['subject'])

        # Ensure the percent notified is updated in the database
        with DBConnection.session() as session:
            proposal = session.execute(active_proposal_query).scalars().first()
            self.assertEqual(1, proposal.percent_notified)

        # Make sure a second alert is not sent during successive calls
        # Note: ``assert_called_once`` includes earlier calls in the test
        self.account.notify()
        mock_send_message.assert_called_once()
