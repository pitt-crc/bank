"""Tests for the ``SlurmAccount`` class"""

from unittest import TestCase

from bank.settings import app_settings
from bank.system import ShellCmd, SlurmAccount

TEST_ACCOUNT = 'this_is_a_test_user'


class AccountLocking(TestCase):
    """Test the locking and unlocking of an account"""

    def runTest(self) -> None:
        account = SlurmAccount(TEST_ACCOUNT)

        account.set_locked_state(True)
        self.assertTrue(account.get_locked_state())

        account.set_locked_state(False)
        self.assertFalse(account.get_locked_state())

        account.set_locked_state(True)
        self.assertTrue(account.get_locked_state())


class AccountUsage(TestCase):
    """Test the getting and setting of account usage values"""

    def setUp(self) -> None:
        """Set the raw suage for the testing account to the given value"""

        self.usage = 1_000
        clusters = ','.join(app_settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={TEST_ACCOUNT} cluster={clusters} set RawUsage={usage}')

    def test_get_usage(self) -> None:
        """Test the recovered account usage matches the value set in setup"""

        account = SlurmAccount(TEST_ACCOUNT)
        for cluster in app_settings.clusters:
            self.assertEqual(self.usage, account.cluster_usage(cluster))

    def test_get_usage_hours(self) -> None:
        """Test the recovered account usage matches the value set in setup"""

        account = SlurmAccount(TEST_ACCOUNT)
        cluster = app_settings.clusters[0]
        usage_seconds = account.cluster_usage(cluster)
        usage_hours = account.cluster_usage(cluster, in_hours=True)

        self.assertGreater(usage_seconds, 0)
        self.assertEqual(int(usage_seconds / 60 / 60), usage_hours)

    def test_reset_usage(self) -> None:
        """Test account usage is zero after being reset"""

        account = SlurmAccount(TEST_ACCOUNT)
        account.reset_raw_usage()
        for cluster in app_settings.clusters:
            self.assertEqual(0, account.cluster_usage(cluster))
