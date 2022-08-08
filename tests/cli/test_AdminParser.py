"""Tests for the ``AdminParser`` class"""

from unittest import TestCase

from bank.cli import AdminParser
from tests._utils import ProposalSetup
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = AdminParser()

    def test_update_status(self) -> None:
        """Test the parsing of arguments by the ``update_status`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'update_status')

    def test_list_locked(self) -> None:
        """Test the parsing of arguments by the ``list_locked`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'list_locked')

    def test_list_unlocked(self) -> None:
        """Test the parsing of arguments by the ``list_unlocked`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'list_unlocked')
