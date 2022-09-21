"""Tests for the ``InvestmentParser`` class"""

from datetime import datetime
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from bank import settings
from bank.cli import InvestmentParser
from bank.exceptions import SlurmAccountNotFoundError
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

        # Attempt to create an investment with a nonexistent slurm account
        with self.assertRaises(SlurmAccountNotFoundError):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --SUs 100')

        # Create an investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --SUs -100')

        # Create an investment, splitting SUs over multiple repetitions 
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --SUs 100 --num_inv 2')

        # Create an investment, providing a negative num_inv amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --SUs 100 --num_inv -1')

        # Create an investment, providing a custom start date
        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --SUs 100 --start {start_date_str}'
        )

        # Create an investment, providing a custom start date with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --SUs 100 --start 09/01/2500')

        # Create an investment, specifying a custom end date
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --SUs 100 --end {end_date_str}')

        # Create an investment, providing a custom start date with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --SUs 100 --end 09/01/2500')

        # Create an investment, specifying a custom start and end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --SUs 100 --start {start_date_str} --end {end_date_str}')

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        # Delete a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'delete {settings.test_account} --ID 0')

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active investment
        self.assert_parser_matches_func_signature(self.parser, f'add_sus {settings.test_account} --SUs 100')

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'add_sus {settings.test_account} --SUs -100')

        # Add SUs a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'add_sus {settings.test_account} --ID 0 --SUs 100')

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'add_sus {settings.test_account} --ID 0 --SUs -100')

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        # Remove SUs from the active investment
        self.assert_parser_matches_func_signature(self.parser, f'subtract_sus {settings.test_account} --SUs 100')

        # Remove SUs from the active investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'subtract_sus {settings.test_account} --SUs -100')

        # Remove SUs from a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'subtract_sus {settings.test_account} --ID 0 --SUs 100')

        # Remove SUs from a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'subtract_sus {settings.test_account} --ID 0 --SUs -100')

    def test_modify_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)

        # Modify the active investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --start {start_date_str}')

        # Modify the active investment's date, changing only the start date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --start 09/01/2500')

        # Modify a specific investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {start_date_str}'
        )

        # Modify a specific investment's date, changing only the start date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --ID 0 --start 09/01/2500')

        # Modify the active investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --end {end_date_str}')

        # Modify the active investment's date, changing only the end date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --end 09/01/2500')

        # Modify a specific investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --end {end_date_str}'
        )

        # Modify a specific investment's date, changing only the end date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'create {settings.test_account} --end 09/01/2500')

        # Modify the active investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --start {start_date_str} --end {end_date_str}'
        )

        # Modify a specific investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {start_date_str} --end {end_date_str}'
        )

    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        # Advance the active investment
        self.assert_parser_matches_func_signature(self.parser, f'advance {settings.test_account} --SUs 100')

        # Advance the active investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'advance {settings.test_account} --SUs -100')

        # Advance a specific investment
        self.assert_parser_matches_func_signature(self.parser, f'advance {settings.test_account} --ID 0 --SUs 100')

        # Advance a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'advance {settings.test_account} --ID 0 --SUs -100')
