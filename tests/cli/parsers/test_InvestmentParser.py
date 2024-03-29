"""Tests for the ``InvestmentParser`` class"""

from datetime import datetime, timedelta
from unittest import TestCase

from bank import settings
from bank.cli.parsers import InvestmentParser
from tests.cli.parsers._utils import CLIAsserts

TEST_ACCOUNT = settings.test_accounts[0]


class Create(CLIAsserts, TestCase):
    """Test the ``create`` subparser"""

    def test_create_investment(self) -> None:
        """Test investment creation providing only required arguments"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['create', '--sus', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['create', 'fake_account_name', '--sus', '100'])

    def test_missing_sus_error(self) -> None:
        """Test a ``SystemExit`` error is raised when no service units are provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --sus'):
            InvestmentParser().parse_args(['create', TEST_ACCOUNT])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        with self.assertRaisesRegex(SystemExit, 'Argument must be a non-negative integer'):
            InvestmentParser().parse_args(['create', TEST_ACCOUNT, '--sus', '-100'])

    def test_accepts_num_inv(self) -> None:
        """Test the parse accepts a ``num_inv`` argument"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --num_inv 2')

    def test_zero_num_inv(self) -> None:
        """Test a ``SystemExit`` error is raised for a zero number of investments"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --num_inv 0')

    def test_negative_num_inv(self) -> None:
        """Test a ``SystemExit`` error is raised for a negative number of investments"""

        # Create an investment using a negative num_inv amount
        with self.assertRaisesRegex(SystemExit, 'Argument must be a non-negative integer'):
            InvestmentParser().parse_args(['create', TEST_ACCOUNT, '--sus', '100', '--num_inv', '-1'])

    def test_custom_dates(self) -> None:
        """Test the specification of custom dates"""

        # Create an investment using a custom start date
        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --start {start_date_str}')

        # Create an investment using a custom end date
        end_date = start_date + timedelta(days=180)
        end_date_str = end_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --end {end_date_str}')

        # Create an investment using a custom start and end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'create {TEST_ACCOUNT} --sus 100 --start {start_date_str} --end {end_date_str}')

    def test_invalid_date_format(self) -> None:
        """Test a ``SystemExit`` error is raised for invalid date formats"""

        # Create an investment using a start date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            InvestmentParser().parse_args([f'create', TEST_ACCOUNT, '--sus', '100', '--start', '09/01/25'])

        # Create an investment using an end date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            InvestmentParser().parse_args([f'create', TEST_ACCOUNT, '--sus', '100', '--end', '09/01/25'])


class Delete(TestCase, CLIAsserts):
    """Test the ``delete`` subparser"""

    def test_delete_investment(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'delete {TEST_ACCOUNT} --id 0')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['delete', '--id', '0'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['delete', 'fake_account_name', '--id', '0'])

    def test_missing_id_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``id`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --id'):
            InvestmentParser().parse_args(['delete', TEST_ACCOUNT])


class Add(TestCase, CLIAsserts):
    """Test the ``add`` subparser"""

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test an investment ID can be specified using the ``--id`` argument"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --id 0 --sus 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['add_sus', '--sus', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['add_sus', 'fake_account_name', '--sus', '100'])

    def test_missing_sus_error(self) -> None:
        """Test a ``SystemExit`` error is raised when no service units are provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --sus'):
            InvestmentParser().parse_args(['add_sus', TEST_ACCOUNT])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        err_msg = 'Argument must be a non-negative integer: -100'

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['add_sus', TEST_ACCOUNT, '--sus', '-100'])

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['add_sus', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])

    def test_zero_sus(self) -> None:
        """Test zero is a valid number of service units"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --sus 0')
        self.assert_parser_matches_func_signature(InvestmentParser(), f'add_sus {TEST_ACCOUNT} --id 0 --sus 0')


class Subtract(TestCase, CLIAsserts):
    """Text the ``subtract`` subparser"""

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test an investment ID can be specified using the ``--id`` argument"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --id 0 --sus 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['subtract_sus', '--sus', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['subtract_sus', 'fake_account_name', '--sus', '100'])

    def test_missing_sus_error(self) -> None:
        """Test a ``SystemExit`` error is raised when no service units are provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --sus'):
            InvestmentParser().parse_args(['subtract_sus', TEST_ACCOUNT])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        err_msg = 'Argument must be a non-negative integer: -100'

        # Add SUs to the active investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['subtract_sus', TEST_ACCOUNT, '--sus', '-100'])

        # Add SUs to a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['subtract_sus', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])

    def test_zero_sus(self) -> None:
        """Test zero is a valid number of service units"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --sus 0')
        self.assert_parser_matches_func_signature(InvestmentParser(), f'subtract_sus {TEST_ACCOUNT} --id 0 --sus 0')


class Modify(TestCase, CLIAsserts):
    """Test the ``modify`` subparser"""

    start_date = datetime.now()
    start_date_str = start_date.strftime(settings.date_format)
    end_date = start_date + timedelta(days=180)
    end_date_str = end_date.strftime(settings.date_format)

    def test_modify_active_investment(self) -> None:
        """Test changing the dates of the currently active proposal"""

        # Modify the active investment's start date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'modify_date {TEST_ACCOUNT} --start {self.start_date_str}')

        # Modify the active investment's end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'modify_date {TEST_ACCOUNT} --end {self.end_date_str}')

        # Modify the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'modify_date {TEST_ACCOUNT} --start {self.start_date_str} --end {self.end_date_str}')

    def test_modify_specific_investment(self) -> None:
        """Test changing the dates while specifying an investment ID"""

        # Modify only the start date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'modify_date {TEST_ACCOUNT} --id 0 --start {self.start_date_str}')

        # Modify only the end date
        self.assert_parser_matches_func_signature(
            InvestmentParser(), f'modify_date {TEST_ACCOUNT} --id 0 --end {self.end_date_str}')

        # Modify the start and end dates
        self.assert_parser_matches_func_signature(
            InvestmentParser(),
            f'modify_date {TEST_ACCOUNT} --id 0 --start {self.start_date_str} --end {self.end_date_str}')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['modify_date', '--start', self.start_date_str])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['modify_date', 'fake_account_name'])

    def test_incorrect_date_format(self) -> None:
        """Test a ``SystemExit`` error is raised for invalid date formats"""

        # Modify the start date using the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            InvestmentParser().parse_args(['modify_date', TEST_ACCOUNT, '--start', '09/01/25'
                                                                                   ''])

        # Modify the end date using the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            InvestmentParser().parse_args(['modify_date', TEST_ACCOUNT, '--end', '09/01/25'])


class Advance(TestCase, CLIAsserts):
    """Test the ``advance`` subparser"""

    def test_advance_sus(self) -> None:
        """Test the parsing of arguments by the ``advance`` command"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'advance {TEST_ACCOUNT} --sus 100')

    def test_investment_id(self) -> None:
        """Test the specification of a specific investment ID"""

        self.assert_parser_matches_func_signature(InvestmentParser(), f'advance {TEST_ACCOUNT} --id 0 --sus 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            InvestmentParser().parse_args(['advance', '--sus', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            InvestmentParser().parse_args(['advance', 'fake_account_name'])

    def test_missing_sus_error(self) -> None:
        """Test a ``SystemExit`` error is raised when no service units are provided"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --sus'):
            InvestmentParser().parse_args(['advance', TEST_ACCOUNT])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        err_msg = 'Argument must be a non-negative integer: -100'

        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['advance', TEST_ACCOUNT, '--sus', '-100'])

        # Advance a specific investment, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            InvestmentParser().parse_args(['advance', TEST_ACCOUNT, '--id', '0', '--sus', '-100'])
