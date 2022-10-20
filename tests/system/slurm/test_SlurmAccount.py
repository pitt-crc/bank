"""Tests for the ``SlurmAccount`` class."""

from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.exceptions import SlurmAccountNotFoundError, SlurmClusterNotFoundError
from bank.system.slurm import Slurm, SlurmAccount


class Instantiation(TestCase):
    """Tests for the instantiation of new instances"""

    def test_error_on_missing_account(self) -> None:
        """Test a ``SlurmAccountNotFoundError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(SlurmAccountNotFoundError):
            SlurmAccount('fake_account')

    def test_valid_account_name(self) -> None:
        """Tet an instance is created successfully for a valid account name"""

        test_account_name = 'account1'
        self.assertEqual(test_account_name, SlurmAccount(test_account_name).account_name)

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(Slurm, 'is_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account')


class CheckAccountExists(TestCase):
    """Tests for the ``check_account_exists`` method"""

    def test_valid_account(self) -> None:
        """Test the return value is ``True`` for an existing account"""

        self.assertTrue(SlurmAccount.check_account_exists('account1'))

    def test_invalid_account(self) -> None:
        """Test the return value is ``True`` for a nonexistant existing account"""

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
