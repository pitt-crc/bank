"""Tests for the ``AccountParser`` class"""

from unittest import TestCase

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

        self.assert_parser_matches_func_signature(self.parser, 'info --account dummy_account')

    def test_lock(self) -> None:
        """Test the parsing of arguments by the ``lock`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'lock --account dummy_account')

    def test_unlock(self) -> None:
        """Test the parsing of arguments by the ``unlock`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'unlock --account dummy_account')

    def test_renew_investment(self) -> None:
        """Test the parsing of arguments by the ``renew`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'renew --account dummy_account')
