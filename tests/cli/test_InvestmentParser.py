"""Tests for the ``InvestmentParser`` class"""

from datetime import datetime
from unittest import TestCase

from bank import settings
from bank.cli import InvestmentParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = InvestmentParser()

    def test_create_investment(self) -> None:
        """Test the parsing of arguments by the ``create`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --repeat 2 --SUs 30 --duration 6')

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'delete {settings.test_account} --ID 0')

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'add {settings.test_account} --ID 0 --SUs 10')

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract {settings.test_account} --ID 0 --SUs 10')

    def test_modify_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0')
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date} --end {date}')


    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            f'advance {settings.test_account} --ID 0 --SUs 10')
