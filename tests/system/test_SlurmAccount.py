from unittest import TestCase, skipIf
from unittest.mock import patch

from bank import settings
from bank.exceptions import NoSuchAccountError
from bank.system import SlurmAccount, RequireRoot

# Skip all tests in this module if slurm is not installed
skipIf(not SlurmAccount.check_slurm_installed(), 'Slurm is not installed on this machine')


class InitExceptions(TestCase):
    """Tests related to exceptions raised during instantiation"""

    def test_error_on_missing_account(self) -> None:
        """Test a ``NoSuchAccountError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(NoSuchAccountError):
            SlurmAccount('fake_account_name_123')

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(SlurmAccount, 'check_slurm_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account_name_123')


@skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
class AccountLocking(TestCase):
    """Test the locking and unlocking of an account"""

    def runTest(self) -> None:
        account = SlurmAccount(settings.test_account)

        account.set_locked_state(False)
        self.assertFalse(account.get_locked_state())

        account.set_locked_state(True)
        self.assertTrue(account.get_locked_state())

        account.set_locked_state(False)
        self.assertFalse(account.get_locked_state())


class AccountUsage(TestCase):
    """Test the retrieval of account usage values"""

    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage in hours matches the value in seconds"""

        account = SlurmAccount(settings.test_account)
        cluster = settings.clusters[0]
        usage_seconds = account.get_cluster_usage(cluster)
        usage_hours = account.get_cluster_usage(cluster, in_hours=True)

        self.assertGreater(usage_seconds, 0)
        self.assertEqual(int(usage_seconds // 60), usage_hours)
