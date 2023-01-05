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
        """Test the account name argument is required"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            AccountParser().parse_args(['info'])


class Lock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``lock`` subparser"""

    def test_all_clusters_flag(self) -> None:
        """Test the ``lock`` accepts the ``--all-clusters`` option"""

        self.assert_parser_matches_func_signature(AccountParser(), f'lock {TEST_ACCOUNT} --all-clusters')

    def test_accepts_cluster_name(self) -> None:
        """Test the ``lock`` command accepts cluster names"""

        self.assert_parser_matches_func_signature(AccountParser(), f'lock {TEST_ACCOUNT} {TEST_CLUSTER}')

    def test_all_clusters_plus_name_error(self) -> None:
        """Test an error is raised when a cluster name is specified with ``--all-clusters``"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                AccountParser(), f'lock {TEST_ACCOUNT} {TEST_CLUSTER} --all-clusters')

    def test_invalid_cluster_error(self) -> None:
        """Test an error is raised for cluster names not defined in application settings"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(AccountParser(), f'lock {TEST_ACCOUNT} fake_cluster_name')

    def test_invalid_account_error(self) -> None:
        """Test an error is raised for account names that do not exist"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(AccountParser(), f'lock fake_account_name --all-clusters')

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(AccountParser(), f'lock fake_account_name {TEST_CLUSTER}')


class Unlock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``unlock`` subparser"""

    def test_all_clusters_flag(self) -> None:
        """Test the ``lock`` accepts the ``--all-clusters`` option"""

        self.assert_parser_matches_func_signature(AccountParser(), f'unlock {TEST_ACCOUNT} --all-clusters')

    def test_accepts_cluster_name(self) -> None:
        """Test the ``lock`` command accepts cluster names"""

        self.assert_parser_matches_func_signature(
            AccountParser(), f'unlock {TEST_ACCOUNT} {TEST_CLUSTER}')

    def test_all_clusters_plus_name_error(self) -> None:
        """Test an error is raised when a cluster name is specified with ``--all-clusters``"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                AccountParser(), f'unlock {TEST_ACCOUNT} {TEST_CLUSTER} --all-clusters')

    def test_invalid_cluster_error(self) -> None:
        """Test an error is raised for cluster names not defined in application settings"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                AccountParser(), f'unlock {TEST_ACCOUNT} fake_cluster_name')

    def test_invalid_account_error(self) -> None:
        """Test an error is raised for account names that do not exist"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(AccountParser(), f'unlock fake_account_name --all-clusters')

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(AccountParser(), f'unlock fake_account_name {TEST_CLUSTER}')
