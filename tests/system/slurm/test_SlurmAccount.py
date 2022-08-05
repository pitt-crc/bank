"""Tests for the ``SlurmAccount`` class."""

from unittest import TestCase, skipIf
from unittest.mock import patch

from bank import settings
from bank.exceptions import SlurmAccountNotFoundError
from bank.system.slurm import Slurm, SlurmAccount


@skipIf(not Slurm.is_installed(), 'Slurm is not installed on this machine')
class InitExceptions(TestCase):
    """Tests for exceptions raised during instantiation"""

    def test_error_on_missing_account(self) -> None:
        """Test a ``SlurmAccountNotFoundError`` error is raised if the specified user account does not exist"""

        with self.assertRaises(SlurmAccountNotFoundError):
            SlurmAccount('fake_account_name_123')

    def test_error_if_slurm_not_installed(self) -> None:
        """Test a ``SystemError`` is raised if ``sacctmgr`` is not installed"""

        with patch.object(SlurmAccount, 'check_slurm_installed', return_value=False), self.assertRaises(SystemError):
            SlurmAccount('fake_account_name_123')


@skipIf(not Slurm.is_installed(), 'Slurm is not installed on this machine')
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
