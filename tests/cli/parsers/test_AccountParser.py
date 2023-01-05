"""Tests for the ``AccountParser`` class"""

from unittest import TestCase

from bank import settings
from bank.cli import AccountParser
from tests._utils import ProposalSetup
from tests.cli.parsers._utils import CLIAsserts


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = AccountParser()

    def test_account_info(self) -> None:
        """Test the parsing of arguments by the ``info`` command"""

        self.assert_parser_matches_func_signature(self.parser, f'info {settings.test_accounts[0]}')

    def test_lock_list_clusters(self) -> None:
        """Test argument parsing for the ``lock`` command`"""

        # Lock on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'lock {settings.test_accounts[0]} --cluster {settings.test_cluster}'
        )

        # Lock on all clusters
        self.assert_parser_matches_func_signature(self.parser, f'lock {settings.test_accounts[0]} --all_clusters')

    def test_unlock_clusters(self) -> None:
        """Test argument parsing for the ``unlock`` command """

        # Unlock on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'unlock {settings.test_accounts[0]} --cluster {settings.test_cluster}'
        )

        # Unlock on a specific cluster
        self.assert_parser_matches_func_signature(self.parser, f'unlock {settings.test_accounts[0]} --all_clusters')
