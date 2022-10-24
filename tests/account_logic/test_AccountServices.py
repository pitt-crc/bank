from datetime import timedelta
from unittest import TestCase, skip
from unittest.mock import patch

import time_machine
from sqlalchemy import join, select

from bank import settings
from bank.account_logic import AccountServices
from bank.orm import Account, Allocation, DBConnection, Investment, Proposal
from bank.system.slurm import SlurmAccount
from tests._utils import InvestmentSetup, ProposalSetup

active_proposal_query = select(Proposal).join(Account) \
    .where(Account.name == settings.test_account) \
    .where(Proposal.is_active)

active_investment_query = select(Investment).join(Account) \
    .where(Account.name == settings.test_account) \
    .where(Investment.is_active)


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

        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(False, settings.test_cluster)

        account_services = AccountServices(settings.test_account)
        account_services.lock(clusters=[settings.test_cluster])
        self.assertTrue(slurm_account.get_locked_state(settings.test_cluster))


class AccountUnlocking(TestCase):
    """Test unlocking the account"""

    def test_account_unlocked_on_cluster(self) -> None:
        """Test the account is unlocked on a given cluster"""

        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(True, settings.test_cluster)

        account_services = AccountServices(settings.test_account)
        account_services.unlock(clusters=[settings.test_cluster])
        self.assertFalse(slurm_account.get_locked_state(settings.test_cluster))


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


class UpdateStatus(ProposalSetup, InvestmentSetup, TestCase):
    """Test update_status functionality for an individual account"""

    def setUp(self) -> None:
        super().setUp()

        self.account = AccountServices(settings.test_account)
        with DBConnection.session() as session:
            active_proposal = session.execute(active_proposal_query).scalars().first()
            self.proposal_end_date = active_proposal.end_date

    # Ensure account usage is a reproducible value for testing
    @patch.object(SlurmAccount, "get_cluster_usage", lambda self, cluster, in_hours: 100)
    def test_locking_single_cluster(self) -> None:
        """Test that update_status locks the account on a single cluster that is exceeding usage limits"""

        # Unlock the account
        slurm_acct = SlurmAccount(settings.test_account)
        slurm_acct.set_locked_state(0, cluster=settings.test_cluster)

        with DBConnection.session() as session:

            # Expired on test cluster, no floating SUs
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_used = 10_000

            # No Investment SUs
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status

        # cluster should be locked due to exceeding usage
        self.assertTrue(slurm_acct.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount, "get_total_usage",
                  lambda self: 100)  # Ensure account usage is a reproducible value for testing
    def test_locking_multiple_clusters(self) -> None:
        """Test that update_status locks the account on one or more clusters but not all clusters"""
        # TODO: Test environment only has a single cluster
        pass

    def test_locked_on_all_clusters(self) -> None:
        """Test that update_status locks the account on all clusters"""
        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(0, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].final_usage = 10_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status

        # clusters should be locked due to lacking an active proposal or investment
        for cluster_name in settings.clusters:
            self.assertTrue(slurm_account.get_locked_state(cluster=cluster_name))

    def test_floating_sus_applied(self) -> None:
        """Test that update_status uses floating SUs to cover usage over limits"""
        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(0, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 11_000
            proposal.allocations.append(Allocation(
                cluster_name="all_clusters",
                service_units_total=1_000,
                service_units_used=0))

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status

        # cluster should be unlocked due to exceeding usage being covered by floating SUs

        joined_tables = join(join(Allocation, Proposal), Account)
        floating_alloc_used_query = select(Allocation.service_units_used) \
            .select_from(joined_tables) \
            .where(Account.name == settings.test_account) \
            .where(Allocation.cluster_name == "all_clusters") \
            .where(Proposal.is_active)

        with DBConnection.session() as session:
            proposal = session.execute(active_proposal_query).scalars().first()
            floating_sus_used = session.execute(floating_alloc_used_query).scalars().first()

            self.assertEqual(1000, floating_sus_used)
            self.assertEqual(proposal.allocations[0].service_units_used, proposal.allocations[0].service_units_total)

        self.assertFalse(slurm_account.get_locked_state(cluster=settings.test_cluster))

    def test_floating_sus_applied_multiple_clusters(self) -> None:
            """Test that update_status uses floating SUs to cover usage over limits"""
            slurm_account = SlurmAccount(settings.test_account)
            slurm_account.set_locked_state(0, cluster=settings.test_cluster)

            with DBConnection.session() as session:
                # Proposal is active and has floating service units
                proposal = session.execute(active_proposal_query).scalars().first()
                # TODO Add floating allocation

                # Investment is expired
                investment = session.execute(active_investment_query).scalars().first()
                investment.current_sus = 0
                investment.withdrawn_sus = investment.service_units

                session.commit()

            self.account.update_status

            # cluster should be locked due to exceeding usage
            # TODO: loop over settings.clusters
            self.assertFalse(slurm_account.get_locked_state(cluster=settings.test_cluster))

    def test_investment_sus_applied(self) -> None:
        """Test that update_status uses investment SUs to cover usage over limits"""

        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(1, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].final_usage = 10_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 1000

            session.commit()

        self.account.update_status

        # cluster should be locked due to exceeding usage
        # TODO: loop over settings.clusters
        self.assertFalse(slurm_account.get_locked_state(cluster=settings.test_cluster))

        with DBConnection.session() as session:
            # TODO: check that investment SUs were used to cover usage
            pass


