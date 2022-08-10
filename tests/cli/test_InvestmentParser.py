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

        # Create an investment, providing only required arguments
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --SUs 100')

        # Create an investment, splitting SUs over multiple repetitions 
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --SUs 100 --repeat 2')

        # Create an investment, providing a custom start date
        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --SUs 100 --start {date}'
        )

        # Create an investment, specifying a custom duration
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --SUs 100 --duration 6')

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        # Delete a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'delete {settings.test_account} --ID 0')

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active investment
        self.assert_parser_matches_func_signature(self.parser, f'add_sus {settings.test_account} --SUs 100')

        # Add SUs a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'add_sus {settings.test_account} --ID 0 --SUs 100')

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        # Remove SUs from the active investment
        self.assert_parser_matches_func_signature(self.parser, f'subtract_sus {settings.test_account} --SUs 100')

        # Remove SUs from a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'subtract {settings.test_account} --ID 0 --SUs 100')

    def test_modify_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        date = datetime.now().strftime(settings.date_format)

        # Modify the active investment's date, changing only the start date
        self.assert_parser_matches_func_signature(self.parser, f'modify_date {settings.test_account} --start {date}')

        # Modify a specific investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date}'
        )

        # Modify the active investment's date, changing only the end date
        self.assert_parser_matches_func_signature(self.parser, f'modify_date {settings.test_account} --end {date}')

        # Modify a specific investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date}'
        )

        # Modify the active investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --start {date} --end {date}'
        )

        # Modify a specific investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date} --end {date}'
        )

    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        # Advance the active investment
        self.assert_parser_matches_func_signature(self.parser, f'advance {settings.test_account} --SUs 100')

        # Advance a specific investment
        self.assert_parser_matches_func_signature(self.parser,f'advance {settings.test_account} --ID 0 --SUs 100')
