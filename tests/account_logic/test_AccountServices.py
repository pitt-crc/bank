from datetime import date, timedelta
from unittest import TestCase, skip
from unittest.mock import patch

import time_machine
from sqlalchemy import join, select

from bank import settings
from bank.account_logic import AccountServices
from bank.orm import Account, Allocation, DBConnection, Investment, Proposal
from bank.system.slurm import SlurmAccount, Slurm
from tests._utils import active_proposal_query, active_investment_query, add_investment_to_test_account, \
    InvestmentSetup, ProposalSetup


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
                  lambda self, cluster, start, end, in_hours=True: {'account1': 50, 'account2': 50})
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


class SetupDBAccountEntry(TestCase):
    """Test first time insertion of the account into the DB"""

    def test_account_inserted(self) -> None:
        """Test the account has an entry in the DB after insertion"""

        account_name = settings.test_accounts[0]
        # Insert an entry into the database for an account with an existing SLURM account
        AccountServices.setup_db_account_entry(account_name)

        with DBConnection.session() as session:
            # Query the DB for the account
            account_query = select(Account).where(Account.name == account_name)
            account = session.execute(account_query).scalars().first()

            # The account entry should not be empty, and the name should match the name provided
            self.assertTrue(account)
            self.assertEqual(account.name, settings.test_accounts[0])

    def test_insertion_idempotence(self) -> None:
        """Test that multiple additions of the same account entry do not overwrite the initial insertion"""

        account_name =  settings.test_accounts[0]
        AccountServices.setup_db_account_entry(account_name)
        AccountServices.setup_db_account_entry(account_name)

        with DBConnection.session() as session:
            account_query = select(Account).where(Account.name == account_name)
            accounts = session.execute(account_query).scalars().all()

        self.assertEqual(len(accounts), 1)

    def test_account_inserted_AccountServices(self) -> None:
        """Test the account has an entry in the DB upon AccountServices object creation"""

        # Create an account services object for an existing SLURM account
        acct = AccountServices(settings.test_accounts[0])

        with DBConnection.session() as session:
            # Query the DB for the account
            account_query = select(Account).where(Account.name == acct._account_name)
            account = session.execute(account_query).scalars().first()

            # The account entry should not be empty, and the name should match the name provided
            self.assertTrue(account)
            self.assertEqual(account.name, acct._account_name)


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


class UpdateStatus(ProposalSetup, InvestmentSetup, TestCase):
    """Test update_status functionality for an individual account"""

    def setUp(self) -> None:
        """Instantiate an AccountServices and SlurmAccount object for the test account"""

        super().setUp()

        self.account = AccountServices(settings.test_accounts[0])

        self.slurm_account = SlurmAccount(settings.test_accounts[0])

    # Ensure account usage is a reproducible value for testing
    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 50, 'account2': 50})
    def test_status_locked_on_single_cluster(self) -> None:
        """Test that update_status locks the account on a single cluster that is exceeding usage limits"""

        # Unlock SLURM account
        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:

            # Expired on test cluster, no floating SUs
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_used = 35_000

            # No Investment SUs
            investment = session.execute(active_investment_query).scalars().first()
            session.delete(investment)

            session.commit()

        self.account.update_status()

        # cluster should be locked due to exceeding usage
        self.assertTrue(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours=True: {'account1': 50, 'account2': 50})
    def test_status_locked_on_multiple_clusters(self) -> None:
        """Test that update_status locks the account on one or more clusters but not all clusters"""
        # TODO: Test environment only has a single cluster
        pass

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours=True: {'account1': 50, 'account2': 50})
    def test_status_locked_on_all_clusters(self) -> None:
        """Test that update_status locks the account on all clusters"""

        # Unlock SLURM account
        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_used = 35_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status()

        # clusters should be locked due to lacking an active proposal or investment
        for cluster in Slurm.cluster_names():
            self.assertTrue(self.slurm_account.get_locked_state(cluster=cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_floating_sus_applied(self) -> None:
        """Test that update_status uses floating SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 11_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status()

        # cluster should be unlocked due to exceeding usage being covered by floating SUs

        joined_tables = join(join(Allocation, Proposal), Account)
        floating_alloc_used_query = select(Allocation.service_units_used) \
            .select_from(joined_tables) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Allocation.cluster_name == "all_clusters") \
            .where(Proposal.is_active)

        with DBConnection.session() as session:
            proposal = session.execute(active_proposal_query).scalars().first()
            floating_sus_used = session.execute(floating_alloc_used_query).scalars().first()

            self.assertEqual(1100, floating_sus_used)
            self.assertEqual(proposal.allocations[0].service_units_used, proposal.allocations[0].service_units_total)

        self.assertFalse(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 100, 'account2': 100})
    def test_status_unlocked_with_floating_sus_exhausted(self) -> None:
        """Test that update_status attempts to use floating SUs to cover usage over limits, but exhausts them
        and ends up using investment SUs instead """

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        joined_tables = join(join(Allocation, Proposal), Account)
        floating_alloc_query = select(Allocation) \
            .select_from(joined_tables) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Allocation.cluster_name == "all_clusters") \
            .where(Proposal.is_active)

        with DBConnection.session() as session:

            floating_alloc = session.execute(floating_alloc_query).scalars().first()
            floating_alloc.service_units_total = 25_000
            floating_alloc.service_units_used = 24_000

            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 11_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 700
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status()

        # cluster should be unlocked due to exceeding usage being covered by floating SUs + investment SUs

        with DBConnection.session() as session:
            proposal = session.execute(active_proposal_query).scalars().first()
            investment = session.execute(active_investment_query).scalars().first()
            floating_alloc = session.execute(floating_alloc_query).scalars().first()

            self.assertEqual(25_000, floating_alloc.service_units_used)
            self.assertEqual(500, investment.current_sus)
            self.assertEqual(proposal.allocations[0].service_units_used, proposal.allocations[0].service_units_total)

        self.assertFalse(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_floating_sus_applied_multiple_clusters(self) -> None:
        """Test that update_status uses floating SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 10_000
            # TODO: need a second allocation on another cluster

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 0
            investment.withdrawn_sus = investment.service_units

            session.commit()

        self.account.update_status()

        joined_tables = join(join(Allocation, Proposal), Account)
        floating_alloc_used_query = select(Allocation.service_units_used) \
            .select_from(joined_tables) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Allocation.cluster_name == "all_clusters") \
            .where(Proposal.is_active)

        # Service units used should equal service units total for the cluster where usage was covered,
        # usage covered should equal the amount needed to bring service_units_used back down to the total
        with DBConnection.session() as session:
            proposal = session.execute(active_proposal_query).scalars().first()
            floating_sus_used = session.execute(floating_alloc_used_query).scalars().first()

            self.assertEqual(proposal.allocations[0].service_units_used, proposal.allocations[0].service_units_total)

            # Floating SUs cover raw usage exceeding total
            self.assertEqual(floating_sus_used, 100)

        # clusters should be unlocked due to exceeding usage being covered by floating SUs
        for cluster in Slurm.cluster_names():
            self.assertFalse(self.slurm_account.get_locked_state(cluster=cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_investment_sus_applied(self) -> None:
        """Test that update_status uses investment SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 35_000

            # Investment is expired
            investment = session.execute(active_investment_query).scalars().first()
            investment.current_sus = 1000

            session.commit()

        self.account.update_status()

        # cluster should be unlocked due to exceeding usage being covered by investment
        self.assertFalse(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

        with DBConnection.session() as session:
            # check that investment SUs were used to cover usage
            investment = session.execute(active_investment_query).scalars().first()

            self.assertEqual(900, investment.current_sus)


    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 550, 'account2': 550})
    def test_status_unlocked_with_multiple_investments_applied(self) -> None:
        """Test that update_status uses investment SUs to cover usage over limits, exhausting the first investment
        and utilizing another investment"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        start = date.today()
        end = start + (1 * timedelta(days=365))

        inv = Investment(
            start_date=start,
            end_date=end,
            service_units=1000,
            current_sus=1000,
            withdrawn_sus=1000,
            rollover_sus=0
        )

        add_investment_to_test_account(inv)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 35_000

            # Investment is expired
            investments = session.execute(active_investment_query).scalars().all()
            investments[0].current_sus = 1000
            investments[0].withdrawn_sus = 2000
            investments[0].service_units = 2000

            session.commit()

        self.account.update_status()

        with DBConnection.session() as session:
            # check that investment SUs were used to cover usage
            investments = session.execute(active_investment_query).scalars().all()

            self.assertEqual(0, investments[0].current_sus)
            self.assertEqual(investments[0].withdrawn_sus, investments[0].service_units)
            self.assertEqual(investments[1].withdrawn_sus, investments[1].service_units)
            self.assertEqual(900, investments[1].current_sus)

        # cluster should be unlocked due to exceeding usage being covered by investment
        self.assertFalse(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, start, end, in_hours: {'account1': 550, 'account2': 550})
    def test_status_locked_with_multiple_sources_exhausted(self) -> None:
        """Test that update_status attempts to use floating and investment SUs to cover usage over limits,
        exhausting the floating SUs and investments"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        start = date.today()
        end = start + (1 * timedelta(days=365))

        inv = Investment(
            start_date=start,
            end_date=end,
            service_units=1000,
            current_sus=1000,
            withdrawn_sus=1000,
            rollover_sus=0
        )

        add_investment_to_test_account(inv)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 36_000

            # Investment is expired
            investments = session.execute(active_investment_query).scalars().all()
            investments[0].current_sus = 1000
            investments[0].withdrawn_sus = 2000
            investments[0].service_units = 2000

            session.commit()

        self.account.update_status()

        with DBConnection.session() as session:
            # check that investment SUs were used to cover usage
            investments = session.execute(active_investment_query).scalars().all()

            self.assertEqual(0, investments[1].current_sus)
            self.assertEqual(investments[1].withdrawn_sus, investments[1].service_units)
            self.assertEqual(0, investments[0].current_sus)

        # cluster should be unlocked due to exceeding usage being covered by investment
        self.assertTrue(self.slurm_account.get_locked_state(cluster=settings.test_cluster))
