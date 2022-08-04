from datetime import timedelta
from unittest import TestCase, skip
from unittest.mock import patch

import time_machine
from sqlalchemy import select

import bank.orm
from bank import settings
from bank.account_logic import AccountServices
from bank.orm import Account, Proposal
from bank.system.slurm import SlurmAccount
from tests._utils import InvestmentSetup, ProposalSetup

active_proposal_query = select(Proposal).join(Account) \
    .where(Account.name == settings.test_account) \
    .where(Proposal.is_active)


class CalculatePercentage(TestCase):
    """Tests for the calculation of percentages"""

    def test_divide_by_zero(self) -> None:
        """Test dividing by zero returns zero"""

        self.assertEqual(0, AccountServices._calculate_percentage(100, 0))

    def test_divide_by_positive(self) -> None:
        """Test dividing by a positive number gives a percentage"""

        self.assertEqual(50, AccountServices._calculate_percentage(1, 2))


@skip('This functionality hasn\'t been fully implimented yet.')
class Renewal(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the renewal of investment accounts"""

    @patch.object(SlurmAccount, "get_cluster_usage", return_value={'user1': 100, 'user2': 200})
    def setUp(self, *args) -> None:
        super().setUp()

        # Fast-forward in time to after the end of the first investment
        investments = self.account._get_investment(self.session)
        end_of_first_inv = investments[0].end_date
        with time_machine.travel(end_of_first_inv + timedelta(days=1)):
            self.account.renew(reset_usage=False)

    def test_new_proposal_is_created(self) -> None:
        """Test a new user proposal is created"""

        # Compare the id of the current proposal with the id of the original proposal
        new_proposal = self.account.get_proposal(self.session)
        self.assertNotEqual(new_proposal.id, self.proposal_id, 'New proposal has same ID as the old one')
        self.assertEqual(
            self.num_proposal_sus, getattr(new_proposal, settings.test_cluster),
            'New proposal does not have same service units as the old one')

        self.assertEqual(new_proposal.proposal_type, bank.orm.Proposal)

    def test_investments_are_rolled_over(self) -> None:
        """Test unused investment service units are rolled over"""

        current_investment = self.account._get_investment(self.session)[0]
        self.assertEqual(self.num_inv_sus * settings.inv_rollover_fraction, current_investment.rollover_sus)


@skip('This functionality hasn\'t been fully implimented yet.')
@patch('smtplib.SMTP.send_message')
class NotifyAccount(ProposalSetup, InvestmentSetup, TestCase):
    """Test for emails sent when locking accounts"""

    def setUp(self) -> None:
        super().setUp()

        self.account = AccountServices(settings.test_account)
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
