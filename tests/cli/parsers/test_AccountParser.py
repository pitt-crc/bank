"""Tests for the ``AccountParser`` class"""

from unittest import TestCase

from bank import settings
from bank.cli import AccountParser
from tests._utils import ProposalSetup
from tests.cli.parsers._utils import CLIAsserts

TEST_ACCOUNT = settings.test_accounts[0]
TEST_CLUSTER = settings.test_cluster


class Info(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``info`` subparser"""

    def test_account_info(self) -> None:
        """Test the parsing of arguments by the ``info`` command"""

        self.assert_parser_matches_func_signature(AccountParser(), f'info {TEST_ACCOUNT}')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account name is not provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            AccountParser().parse_args(['info'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account does not exist"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            AccountParser().parse_args(['info', 'fake_account'])


class Lock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``lock`` subparser"""

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account name is not provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            AccountParser().parse_args(['lock'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account does not exist"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            AccountParser().parse_args(['lock', 'fake_account_name', '--all-clusters'])

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            AccountParser().parse_args(['lock', 'fake_account_name', '--clusters', TEST_CLUSTER])

    def test_all_clusters_flag(self) -> None:
        """Test the ``lock`` accepts the ``--all-clusters`` option"""

        self.assert_parser_matches_func_signature(AccountParser(), f'lock {TEST_ACCOUNT} --all-clusters')

    def test_accepts_cluster_name(self) -> None:
        """Test the ``lock`` command accepts individual cluster names"""

        self.assert_parser_matches_func_signature(AccountParser(), f'lock {TEST_ACCOUNT} --clusters {TEST_CLUSTER}')

    def test_invalid_cluster_error(self) -> None:
        """Test a ``SystemExit`` error is raised for cluster names not defined in application settings"""

        with self.assertRaisesRegex(SystemExit, "invalid choice: 'fake_cluster_name'"):
            AccountParser().parse_args(['lock', TEST_ACCOUNT, '--clusters', 'fake_cluster_name'])

    def test_all_clusters_plus_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised when a cluster name and ``--all-clusters`` are both specified"""

        with self.assertRaisesRegex(SystemExit, 'argument --all-clusters: not allowed with argument --clusters'):
            AccountParser().parse_args(['lock', TEST_ACCOUNT, '--clusters', TEST_CLUSTER, '--all-clusters'])


class Unlock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``unlock`` subparser"""

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account name is not provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            AccountParser().parse_args(['unlock'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised if the account does not exist"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            AccountParser().parse_args(['unlock', 'fake_account_name', '--all-clusters'])

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            AccountParser().parse_args(['unlock', 'fake_account_name', '--clusters', TEST_CLUSTER])

    def test_all_clusters_flag(self) -> None:
        """Test the ``unlock`` accepts the ``--all-clusters`` option"""

        self.assert_parser_matches_func_signature(AccountParser(), f'unlock {TEST_ACCOUNT} --all-clusters')

    def test_accepts_cluster_name(self) -> None:
        """Test the ``unlock`` command accepts cluster names"""

        self.assert_parser_matches_func_signature(AccountParser(), f'unlock {TEST_ACCOUNT} --clusters {TEST_CLUSTER}')

    def test_invalid_cluster_error(self) -> None:
        """Test a ``SystemExit`` error is raised for cluster names not defined in application settings"""

        with self.assertRaisesRegex(SystemExit, "invalid choice: 'fake_cluster_name'"):
            AccountParser().parse_args(['unlock', TEST_ACCOUNT, '--clusters', 'fake_cluster_name'])

    def test_all_clusters_plus_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised when a cluster name and ``--all-clusters`` are both specified"""

        with self.assertRaisesRegex(SystemExit, 'argument --all-clusters: not allowed with argument --clusters'):
            AccountParser().parse_args(['unlock', TEST_ACCOUNT, '--clusters', TEST_CLUSTER, '--all-clusters'])
