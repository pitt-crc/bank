"""Tests for the ``SlurmAccount`` class."""

from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.exceptions import SlurmAccountNotFoundError, SlurmClusterNotFoundError
from bank.system.slurm import Slurm, SlurmAccount


class InitExceptions(TestCase):
    """Tests for exceptions raised during instantiation"""

    def test_error_on_missing_account(self) -> None:
        """Test a ``SlurmAccountNotFoundError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(SlurmAccountNotFoundError):
            SlurmAccount('fake_account_name_123')

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(Slurm, 'is_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account_name_123')


class AccountLocking(TestCase):
    """Test the account is locked/unlocked by the appropriate getters/setters"""

    def test_account_status_updated(self) -> None:
        """Test the account is successfully locked/unlocked"""

        account = SlurmAccount(settings.test_account)
        account.set_locked_state(False, settings.test_cluster)
        self.assertFalse(account.get_locked_state(settings.test_cluster))

        account.set_locked_state(True, settings.test_cluster)
        self.assertTrue(account.get_locked_state(settings.test_cluster))

        account.set_locked_state(False, settings.test_cluster)
        self.assertFalse(account.get_locked_state(settings.test_cluster))

    def test_set_invalid_cluster(self) -> None:
        """Test an error is raised when setting the lock state for a nonexistent cluster"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(SlurmClusterNotFoundError):
            account.set_locked_state(True, 'fake_cluster')

        with self.assertRaises(SlurmClusterNotFoundError):
            account.set_locked_state(False, 'fake_cluster')

    def test_get_invalid_cluster(self) -> None:
        """Test an error is raised when getting the lock state for a nonexistent cluster"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(SlurmClusterNotFoundError):
            account.get_locked_state('fake_cluster')


class AccountUsage(TestCase):
    """Test the retrieval of account usage values"""

    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage in hours matches the value in seconds"""

        account = SlurmAccount(settings.test_account)
        cluster = settings.clusters[0]
        usage_seconds = account.get_cluster_usage(cluster)
        usage_hours = account.get_cluster_usage(cluster, in_hours=True)

        test_user = next(iter(usage_seconds.keys()))
        test_usage_seconds = usage_seconds[test_user]
        test_usage_hours = usage_hours[test_user]

        self.assertGreater(test_usage_seconds, 0)
        self.assertEqual(int(test_usage_seconds // 60), test_usage_hours)
