"""Tests for the ``InvestmentParser`` class"""

from datetime import datetime
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from bank import settings
from bank.cli import InvestmentParser
from tests.cli.parsers._utils import CLIAsserts

TEST_ACCOUNT = settings.test_accounts[0]


class Create(CLIAsserts, TestCase):
    """Test the ``create`` subparser"""

    def test_create_investment(self) -> None:
        """Test investment creation providing only required arguments"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100')

    def test_split_sus(self) -> None:
        """Test investment creation splitting SUs over multiple repetitions"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --num_inv 2')

    def test_custom_dates(self) -> None:
        """Test the specification of custom dates"""

        # Create an investment, providing a custom start date
        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --start {start_date_str}')

        # Create an investment, specifying a custom end date
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --end {end_date_str}')

        # Create an investment, specifying a custom start and end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --start {start_date_str} --end {end_date_str}')

    def test_invalid_date_format(self) -> None:
        """Test and error is raised for invalid date formats"""

        # Create an investment, providing a custom start date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            InvestmentParser().parse_args([f'create', TEST_ACCOUNT, '--sus', '100', '--start', '09/01/2500'])

        # Create an investment, providing a custom end date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            InvestmentParser().parse_args([f'create', TEST_ACCOUNT, '--sus', '100', '--end', '09/01/2500'])

    def test_missing_slurm_account(self) -> None:
        """Test a ``SlurmAccountNotFoundError`` is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['create', 'fake_account_name', '--sus', '100'])

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['create', TEST_ACCOUNT, '--sus', '-100'])

    def test_negative_num_inv(self) -> None:
        """Test and error is raised for a negative number of investments"""

        # Create an investment, providing a negative num_inv amount
        with self.assertRaisesRegex(SystemExit, 'Number of investments must be a positive integer'):
            InvestmentParser().parse_args(['create', TEST_ACCOUNT, '--sus', '100', '--num_inv', '-1'])


class Delete(TestCase, CLIAsserts):
    """Test the ``delete`` subparser"""

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        # Delete a specific investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'delete {TEST_ACCOUNT} --id 0')


class Add(TestCase, CLIAsserts):
    """Test the ``add`` subparser"""

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        # Add SUs a specific investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --id 0 --sus 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['add_sus', TEST_ACCOUNT, '--sus', '-100'])

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['add_sus', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])


class Subtract(TestCase, CLIAsserts):
    """Text the ``subtract`` subparser"""

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --id 0 --sus 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['subtract_sus', TEST_ACCOUNT, '--sus', '-100'])

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['subtract_sus', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])


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
            f'modify_date {TEST_ACCOUNT} --start {start_date_str}')

        # Modify the active investment's date, changing only the start date, but with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {TEST_ACCOUNT} --start 09/01/2500')

        # Modify a specific investment's date, changing only the start date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --id 0 --start {start_date_str}'
        )

        # Modify a specific investment's date, changing only the start date, but with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {TEST_ACCOUNT} --id 0 --start 09/01/2500')

        # Modify the active investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --end {end_date_str}')

        # Modify the active investment's date, changing only the end date, but with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {TEST_ACCOUNT} --end 09/01/2500')

        # Modify a specific investment's date, changing only the end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --id 0 --end {end_date_str}'
        )

        # Modify a specific investment's date, changing only the end date, but with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse given date'):
            self.assert_parser_matches_func_signature(
                InvestmentParser(),
                f'create {TEST_ACCOUNT} --end 09/01/2500')

        # Modify the active investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --start {start_date_str} --end {end_date_str}'
        )

        # Modify a specific investment's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --id 0 --start {start_date_str} --end {end_date_str}'
        )


class Advance(TestCase, CLIAsserts):
    """Test the ``advance`` subparser"""

    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'advance {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        # Advance a specific investment
        self.assert_parser_matches_func_signature(InvestmentParser(), f'advance {TEST_ACCOUNT} --id 0 --sus 100')

    def test_negative_sus(self) -> None:
        """Test an error is raised for negative service units"""

        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['advance', TEST_ACCOUNT, '--sus', '-100'])

        # Advance a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, 'SUs must be a positive integer'):
            InvestmentParser().parse_args(['advance', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])
