"""Tests for the ``SlurmAccount`` class."""

from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.exceptions import AccountNotFoundError, ClusterNotFoundError
from bank.system.slurm import Slurm, SlurmAccount


class Instantiation(TestCase):
    """Tests for the instantiation of new instances"""

    def test_error_on_missing_account(self) -> None:
        """Test a ``AccountNotFoundError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(AccountNotFoundError):
            SlurmAccount('fake_account')

    def test_valid_account_name(self) -> None:
        """Tet an instance is created successfully for a valid account name"""

        self.assertEqual(settings.test_account, SlurmAccount(settings.test_account).account_name)

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(Slurm, 'is_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account')


class CheckAccountExists(TestCase):
    """Tests for the ``check_account_exists`` method"""

    def test_valid_account(self) -> None:
        """Test the return value is ``True`` for an existing account"""

        self.assertTrue(SlurmAccount.check_account_exists(settings.test_account))

    def test_invalid_account(self) -> None:
        """Test the return value is ``True`` for a non-existant existing account"""

        self.assertFalse(SlurmAccount.check_account_exists('fake_account'))


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
        """Test a ``ClusterNotFoundError`` error is raised when setting a nonexistent cluster"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(True, 'fake_cluster')

        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(False, 'fake_cluster')

    def test_set_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when setting a blank cluster name"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(True, '')

        with self.assertRaises(ClusterNotFoundError):
            account.set_locked_state(False, '')

    def test_get_invalid_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when getting a nonexistent cluster"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.get_locked_state('fake_cluster')

    def test_get_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when getting a blank cluster name"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.get_locked_state('')


class GetClusterUsage(TestCase):
    """Test fetching an account's cluster usage via the ``get_cluster_usage`` method"""

    def test_error_invalid_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when passed a nonexistent cluster"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.get_cluster_usage('fake_cluster')

    def test_error_blank_cluster(self) -> None:
        """Test a ``ClusterNotFoundError`` error is raised when passed a blank cluster name"""

        account = SlurmAccount(settings.test_account)
        with self.assertRaises(ClusterNotFoundError):
            account.get_cluster_usage('')
