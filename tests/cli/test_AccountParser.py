"""Tests for the ``AccountParser`` class"""

from unittest import TestCase

from bank import settings
from bank.cli import AccountParser
from tests._utils import ProposalSetup
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = AccountParser()

    def test_account_info(self) -> None:
        """Test the parsing of arguments by the ``info`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'info --account {settings.test_account}')

    def test_lock_list_clusters(self) -> None:
        """Test argument parsing by the ``lock`` command with `--clusters`"""

        self.assert_parser_matches_func_signature(
            self.parser,
            (f'lock --account {settings.test_account} '
             f'--cluster {settings.test_cluster}')
        )

    def test_lock_all_clusters(self) -> None:
        """ Test argument parsing by the ``lock`` command with `--all`"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'lock --account {settings.test_account} --all')

    def test_unlock_list_clusters(self) -> None:
        """Test argument parsing by the ``unlock`` command with `--clusters`"""
        self.assert_parser_matches_func_signature(
            self.parser,
            (f'unlock --account {settings.test_account} '
             f'--cluster {settings.test_cluster}')
        )

    def test_unlock_all_clusters(self) -> None:
        """Test arguments parsing by the ``unlock`` command with `--all`"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'unlock --account {settings.test_account} --all')
