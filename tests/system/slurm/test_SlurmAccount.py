"""Tests for the ``SlurmAccount`` class."""

from unittest import TestCase, skip
from unittest.mock import patch

from bank.exceptions import AccountNotFoundError, ClusterNotFoundError
from bank.system.slurm import Slurm, SlurmAccount
from tests import TestSettings

class Instantiation(TestCase):
    """Test the instantiation of new instances"""

    def test_error_on_missing_account(self) -> None:
        """Test an ``AccountNotFoundError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(AccountNotFoundError):
            SlurmAccount('fake_account')

    def test_valid_account_name(self) -> None:
        """Test an instance is created successfully for a valid account name"""

        account = SlurmAccount(TestSettings.test_accounts[0])
        self.assertEqual(settings.test_accounts[0], account.account_name)

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(Slurm, 'is_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account')


class CheckAccountExists(TestCase):
    """Tests for the ``check_account_exists`` method"""

    def test_valid_account(self) -> None:
        """Test the return value is ``True`` for an existing account"""

        self.assertTrue(SlurmAccount.check_account_exists(settings.test_accounts[0]))

    def test_invalid_account(self) -> None:
        """Test the return value is ``False`` for a non-existent account"""

        self.assertFalse(SlurmAccount.check_account_exists('fake_account'))


class AccountLocking(TestCase):
    """Test the account is locked/unlocked by the appropriate getters/setters"""

    def test_account_status_updated(self) -> None:
        """Test the account is successfully locked/unlocked"""

        account = SlurmAccount(settings.test_accounts[0])
        account.set_locked_state(False, settings.test_cluster)
        self.assertFalse(account.get_locked_state(settings.test_cluster))

        account.set_locked_state(True, settings.test_cluster)
        self.assertTrue(account.get_locked_state(settings.test_cluster))

        account.set_locked_state(False, settings.test_cluster)
        self.assertFalse(account.get_locked_state(settings.test_cluster))


class SetLockedState(TestCase):
    """Tests for the ``set_locked_state`` method"""

    def test_set_invalid_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when setting a nonexistent cluster"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(True, 'fake_cluster')

        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(False, 'fake_cluster')

    def test_set_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when setting a blank cluster name"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(True, '')

        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(False, '')


class GetLockedState(TestCase):
    """Tests for the ``get_locked_state`` method"""

    def test_get_invalid_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when getting a nonexistent cluster"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.get_locked_state('fake_cluster')

    def test_get_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when getting a blank cluster name"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.get_locked_state('')


class GetClusterUsage(TestCase):
    """Test fetching an account's cluster usage via the ``get_cluster_usage_per_user`` method"""

    def test_error_invalid_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when passed a nonexistent cluster"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.get_cluster_usage_per_user('fake_cluster')

    def test_error_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when passed a blank cluster name"""

        account = SlurmAccount(settings.test_accounts[0])
        with self.assertRaises(ClusterNotFoundError):
            account.get_cluster_usage_per_user('')

    @skip('This functionality relies on setting up SLURM account with non-zero usage in the DB.')
    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage in hours matches the value in seconds"""

        account = SlurmAccount(settings.test_accounts[0])
        cluster = settings.test_cluster
        usage_seconds = account.get_cluster_usage_per_user(cluster)
        usage_hours = account.get_cluster_usage_per_user(cluster, in_hours=True)

        test_user = next(iter(usage_seconds.keys()))
        test_usage_seconds = usage_seconds[test_user]
        test_usage_hours = usage_hours[test_user]

        self.assertGreater(test_usage_seconds, 0)
        self.assertEqual(int(test_usage_seconds // 60), test_usage_hours)
