from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.account_logic import AdminServices
from bank.system.slurm import SlurmAccount
from tests._utils import EmptyAccountSetup, ProposalSetup, InvestmentSetup


class FindUnlockedAccounts(EmptyAccountSetup, TestCase):
    """Test finding unlocked accounts via the ``find_unlocked`` method"""

    def setUp(self) -> None:
        """Instantiate a SlurmAccount and AdminServices objects for finding account tests"""
        super().setUp()
        self.slurm_account1 = SlurmAccount(settings.test_accounts[0])
        self.slurm_account2 = SlurmAccount(settings.test_accounts[1])
        self.admin_services = AdminServices()

    def test_unlocked_accounts_found(self) -> None:
        """Test that an unlocked accounts are found"""

        # Unlock multiple accounts
        self.slurm_account1.set_locked_state(False, settings.test_cluster)
        self.slurm_account2.set_locked_state(False, settings.test_cluster)

        # The accounts should be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[settings.test_cluster])
        self.assertIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[settings.test_cluster])

    def test_locked_accounts_not_found(self) -> None:
        """Test that locked accounts are not found"""

        # Lock multiple accounts
        self.slurm_account1.set_locked_state(True, settings.test_cluster)
        self.slurm_account2.set_locked_state(True, settings.test_cluster)

        # The accounts should not be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertNotIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[settings.test_cluster])
        self.assertNotIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[settings.test_cluster])

    def test_unlocked_accounts_only_found(self) -> None:
        """Test that, amongst accounts that are locked, only unlocked accounts are found"""

        # Lock one account and unlock another
        self.slurm_account1.set_locked_state(True, settings.test_cluster)
        self.slurm_account2.set_locked_state(False, settings.test_cluster)

        # The unlocked account should be in the list of unlocked accounts, while the locked account should not
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertNotIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[settings.test_cluster])
        self.assertIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[settings.test_cluster])


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
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_locked_on_single_cluster(self) -> None:
        """Test that update_status locks the account on a single cluster that is exceeding usage limits"""

        # Unlock SLURM account
        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:

            # Expired on test cluster, no floating SUs
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_used = 10_000

            # No Investment SUs
            investment = session.execute(active_investment_query).scalars().first()
            session.delete(investment)

            session.commit()

        self.account.update_status()

        # cluster should be locked due to exceeding usage
        self.assertTrue(self.slurm_account.get_locked_state(cluster=settings.test_cluster))

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_locked_on_multiple_clusters(self) -> None:
        """Test that update_status locks the account on one or more clusters but not all clusters"""
        # TODO: Test environment only has a single cluster
        pass

    @patch.object(SlurmAccount,
                  "get_cluster_usage_per_user",
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_locked_on_all_clusters(self) -> None:
        """Test that update_status locks the account on all clusters"""

        # Unlock SLURM account
        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_used = 10_000

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
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_floating_sus_applied(self) -> None:
        """Test that update_status uses floating SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 11_000
            proposal.allocations.append(Allocation(
                cluster_name="all_clusters",
                service_units_total=10_000,
                service_units_used=0))

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
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_floating_sus_applied_multiple_clusters(self) -> None:
        """Test that update_status uses floating SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is active and has floating service units
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 10_000
            # TODO: need a second allocation on another cluster

            proposal.allocations.append(Allocation(
                cluster_name="all_clusters",
                service_units_total=10_000,
                service_units_used=0))

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
                  lambda self, cluster, in_hours: {'account1': 50, 'account2': 50})
    def test_status_unlocked_with_investment_sus_applied(self) -> None:
        """Test that update_status uses investment SUs to cover usage over limits"""

        self.slurm_account.set_locked_state(False, cluster=settings.test_cluster)

        with DBConnection.session() as session:
            # Proposal is expired
            proposal = session.execute(active_proposal_query).scalars().first()
            proposal.allocations[0].service_units_total = 10_000
            proposal.allocations[0].service_units_used = 10_000

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
