"""Tests for the ``SlurmAccount`` class"""

from unittest import TestCase, skipIf

from bank.settings import app_settings
from bank.system import SlurmAccount, RequireRoot


@skipIf(not RequireRoot.check_user_is_root(), 'Cannot run tests that modify account locks without root permissions')
class AccountLocking(TestCase):
    """Test the locking and unlocking of an account"""

    def runTest(self) -> None:
        account = SlurmAccount(app_settings.test_account)

        account.set_locked_state(False)
        self.assertFalse(account.get_locked_state())

        account.set_locked_state(True)
        self.assertTrue(account.get_locked_state())

        account.set_locked_state(False)
        self.assertFalse(account.get_locked_state())


class AccountUsage(TestCase):
    """Test the getting and setting of account usage values"""

    @skipIf(not SlurmAccount.check_slurm_installed(), 'Slurm is not installed on this machine')
    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage matches the value set in setup"""

        account = SlurmAccount(app_settings.test_account)
        cluster = app_settings.clusters[0]
        usage_seconds = account.get_cluster_usage(cluster)
        usage_hours = account.get_cluster_usage(cluster, in_hours=True)

        self.assertGreater(usage_seconds, 0)
        self.assertEqual(int(usage_seconds // 60), usage_hours)
