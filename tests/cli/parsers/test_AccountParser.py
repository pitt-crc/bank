"""Tests for the ``AccountParser`` class"""

from unittest import TestCase

from bank import settings
from bank.cli import AccountParser
from tests._utils import ProposalSetup
from tests.cli.parsers._utils import CLIAsserts


class Info(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``info`` subparser"""

    def test_account_info(self) -> None:
        """Test the parsing of arguments by the ``info`` command"""

        self.assert_parser_matches_func_signature(AccountParser(), f'info {settings.test_accounts[0]}')


class Lock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``lock`` subparser"""

    def test_lock_all_clusters(self) -> None:
        """Test argument parsing for the ``lock`` command with ``--all-clusters`` specified"""

        self.assert_parser_matches_func_signature(AccountParser(), f'lock {settings.test_accounts[0]} --all-clusters')

    def test_lock_single_cluster(self) -> None:
        """Test argument parsing for the ``lock`` command for a single cluster name"""

        self.assert_parser_matches_func_signature(
            AccountParser(), f'lock {settings.test_accounts[0]} --cluster {settings.test_cluster}')


class Unlock(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``unlock`` subparser"""

    def test_unlock_single_cluster(self) -> None:
        """Test argument parsing for the ``unlock`` command for a single cluster name"""

        self.assert_parser_matches_func_signature(AccountParser(), f'unlock {settings.test_accounts[0]} --all-clusters')

    def test_unlock_all_clusters(self) -> None:
        """Test argument parsing for the ``unlock`` command with ``--all-clusters`` specified"""

        self.assert_parser_matches_func_signature(
            AccountParser(), f'unlock {settings.test_accounts[0]} --cluster {settings.test_cluster}')
