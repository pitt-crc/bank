"""Tests for the ``SlurmAccount`` class"""

from unittest import TestCase

from bank.settings import app_settings
from bank.system import ShellCmd, SlurmAccount


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

    def setUp(self) -> None:
        """Set the raw usage for the testing account to the given value"""

        self.usage = 1_000
        clusters = ','.join(app_settings.clusters)
        cmd = ShellCmd(f'sacctmgr -i modify account where account={app_settings.test_account} cluster={clusters} set RawUsage={self.usage}')
        cmd.raise_err()

    def test_get_usage(self) -> None:
        """Test the recovered account usage matches the value set in setup"""

        account = SlurmAccount(app_settings.test_account)
        for cluster in app_settings.clusters:
            self.assertEqual(self.usage, account.cluster_usage(cluster))

    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage matches the value set in setup"""

        account = SlurmAccount(app_settings.test_account)
        cluster = app_settings.clusters[0]
        usage_seconds = account.cluster_usage(cluster)
        usage_hours = account.cluster_usage(cluster, in_hours=True)

        self.assertGreater(usage_seconds, 0)
        self.assertEqual(int(usage_seconds / 60 / 60), usage_hours)

    def test_reset_usage(self) -> None:
        """Test account usage is zero after being reset"""

        account = SlurmAccount(app_settings.test_account)
        account.reset_raw_usage()
        for cluster in app_settings.clusters:
            self.assertEqual(0, account.cluster_usage(cluster))
