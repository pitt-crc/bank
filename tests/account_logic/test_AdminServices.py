from unittest import TestCase

from sqlalchemy import select

from bank.account_logic import AdminServices
from bank.system.slurm import SlurmAccount
from tests import TestSettings
from tests._utils import EmptyAccountSetup


class FindUnlockedAccounts(EmptyAccountSetup, TestCase):
    """Test finding unlocked accounts via the ``find_unlocked`` method"""

    def setUp(self) -> None:
        """Instantiate a SlurmAccount and AdminServices objects for finding account tests"""
        super().setUp()
        self.slurm_account1 = SlurmAccount(TestSettings.test_accounts[0])
        self.slurm_account2 = SlurmAccount(TestSettings.test_accounts[1])
        self.admin_services = AdminServices()

    def test_unlocked_accounts_found(self) -> None:
        """Test that an unlocked accounts are found"""

        # Unlock multiple accounts
        self.slurm_account1.set_locked_state(False, TestSettings.test_cluster)
        self.slurm_account2.set_locked_state(False, TestSettings.test_cluster)

        # The accounts should be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])
        self.assertIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])

    def test_locked_accounts_not_found(self) -> None:
        """Test that locked accounts are not found"""

        # Lock multiple accounts
        self.slurm_account1.set_locked_state(True, TestSettings.test_cluster)
        self.slurm_account2.set_locked_state(True, TestSettings.test_cluster)

        # The accounts should not be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertNotIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])
        self.assertNotIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])

    def test_unlocked_accounts_only_found(self) -> None:
        """Test that, amongst accounts that are locked, only unlocked accounts are found"""

        # Lock one account and unlock another
        self.slurm_account1.set_locked_state(True, TestSettings.test_cluster)
        self.slurm_account2.set_locked_state(False, TestSettings.test_cluster)

        # The unlocked account should be in the list of unlocked accounts, while the locked account should not
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertNotIn(self.slurm_account1.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])
        self.assertIn(self.slurm_account2.account_name, unlocked_accounts_by_cluster[TestSettings.test_cluster])
