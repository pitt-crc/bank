"""Tests for the ``InvestmentParser`` class"""

from datetime import datetime
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from bank import settings
from bank.cli import InvestmentParser
from bank.exceptions import SlurmAccountNotFoundError
from tests.cli.parsers._utils import CLIAsserts


class Create(CLIAsserts, TestCase):
    """Test the ``create`` subparser"""

    def test_create_investment(self) -> None:
        """Test investment creation providing only required arguments"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {settings.test_accounts[0]} --SUs 100')

    def test_split_sus(self) -> None:
        """Test investment creation splitting SUs over multiple repetitions"""

        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'create {settings.test_accounts[0]} --SUs 100 --num_inv 2')

    def test_custom_dates(self) -> None:
        """Test the specification of custom dates"""

        # Create an investment, providing a custom start date
        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'create {settings.test_accounts[0]} --SUs 100 --start {start_date_str}'
        )

        # Create an investment, specifying a custom end date
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'create {settings.test_accounts[0]} --SUs 100 --end {end_date_str}')

        # Create an investment, specifying a custom start and end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'create {settings.test_accounts[0]} --SUs 100 --start {start_date_str} --end {end_date_str}')

    def test_invalid_date_format(self) -> None:
        """Test and error is raised for invalid date formats"""

        # Create an investment, providing a custom start date with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --SUs 100 --start 09/01/2500')

        # Create an investment, providing a custom end date with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --SUs 100 --end 09/01/2500')

    def test_missing_slurm_account(self) -> None:
        """Test a ``SlurmAccountNotFoundError`` is raised for a missing slurm account"""

        with self.assertRaises(SlurmAccountNotFoundError):
            self.assert_parser_matches_func_signature(InvestmentParser(), f'create fake_account_name --SUs 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(), f'create {settings.test_accounts[0]} --SUs -100')

    def test_negative_num_inv(self) -> None:
        """Test and error is raised for a negative number of investments"""

        # Create an investment, providing a negative num_inv amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --SUs 100 --num_inv -1')


class Delete(TestCase, CLIAsserts):
    """Test the ``delete`` subparser"""

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        # Delete a specific investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'delete {settings.test_accounts[0]} --ID 0')


class Add(TestCase, CLIAsserts):
    """Test the ``add`` subparser"""

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {settings.test_accounts[0]} --SUs 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        # Add SUs a specific investment
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'add_sus {settings.test_accounts[0]} --ID 0 --SUs 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(), f'add_sus {settings.test_accounts[0]} --SUs -100')

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(), f'add_sus {settings.test_accounts[0]} --ID 0 --SUs -100')


class Subtract(TestCase, CLIAsserts):
    """Text the ``subtract`` subparser"""

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'subtract_sus {settings.test_accounts[0]} --SUs 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'subtract_sus {settings.test_accounts[0]} --ID 0 --SUs 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'subtract_sus {settings.test_accounts[0]} --SUs -100')

        # Remove SUs from a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'subtract_sus {settings.test_accounts[0]} --ID 0 --SUs -100')


class Modify(TestCase, CLIAsserts):
    """Test the ``modify`` subparser"""

    def test_modify_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)

        # Modify the active investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --start {start_date_str}')

        # Modify the active investment's date, changing only the start date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --start 09/01/2500')

        # Modify a specific investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --ID 0 --start {start_date_str}'
        )

        # Modify a specific investment's date, changing only the start date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --ID 0 --start 09/01/2500')

        # Modify the active investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --end {end_date_str}')

        # Modify the active investment's date, changing only the end date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --end 09/01/2500')

        # Modify a specific investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --ID 0 --end {end_date_str}'
        )

        # Modify a specific investment's date, changing only the end date, but with the wrong format
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {settings.test_accounts[0]} --end 09/01/2500')

        # Modify the active investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --start {start_date_str} --end {end_date_str}'
        )

        # Modify a specific investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {settings.test_accounts[0]} --ID 0 --start {start_date_str} --end {end_date_str}'
        )


class Advance(TestCase, CLIAsserts):
    """Test the ``advance`` subparser"""

    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'advance {settings.test_accounts[0]} --SUs 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        # Advance a specific investment
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'advance {settings.test_accounts[0]} --ID 0 --SUs 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'advance {settings.test_accounts[0]} --SUs -100')

        # Advance a specific investment, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'advance {settings.test_accounts[0]} --ID 0 --SUs -100')
