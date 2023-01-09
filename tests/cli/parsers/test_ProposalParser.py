"""Tests for the ``ProposalParser`` class"""

from datetime import datetime
from unittest import TestCase

from dateutil.relativedelta import relativedelta

from bank import settings
from bank.cli import ProposalParser
from tests._utils import ProposalSetup
from tests.cli.parsers._utils import CLIAsserts

TEST_ACCOUNT = settings.test_accounts[0]
TEST_CLUSTER = settings.test_cluster


class Create(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``create`` subparser"""

    def test_create_proposal(self) -> None:
        """Test proposal creation providing only required arguments"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'create {TEST_ACCOUNT} --{TEST_CLUSTER} 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            ProposalParser().parse_args(['create', f'--{TEST_CLUSTER}', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            ProposalParser().parse_args(['create', 'fake_account_name', f'--{TEST_CLUSTER}', '100'])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        with self.assertRaisesRegex(SystemExit, 'Argument must be a non-negative integer'):
            ProposalParser().parse_args(['create', TEST_ACCOUNT, f'--{TEST_CLUSTER}', '-100'])

    def test_custom_dates(self) -> None:
        """Test the specification of custom dates"""

        # Create a proposal using a custom start date
        start_date = datetime.now()
        start_date_str = start_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            ProposalParser(), f'create {TEST_ACCOUNT} --{TEST_CLUSTER} 100 --start {start_date_str}')

        # Create a proposal using a custom end date
        end_date = start_date + relativedelta(months=6)
        end_date_str = end_date.strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            ProposalParser(), f'create {TEST_ACCOUNT} --{TEST_CLUSTER} 100 --end {end_date_str}')

        # Create a proposal using a custom start and end date
        self.assert_parser_matches_func_signature(
            ProposalParser(),
            f'create {TEST_ACCOUNT} --{TEST_CLUSTER} 100 --start {start_date_str} --end {end_date_str}')

    def test_invalid_date_format(self) -> None:
        """Test a ``SystemExit`` error is raised for invalid date formats"""

        # Create a proposal using a start date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            ProposalParser().parse_args([f'create', TEST_ACCOUNT, f'--{TEST_CLUSTER}', '100', '--start', '09/01/2500'])

        # Create a proposal using an end date with the wrong format
        with self.assertRaisesRegex(SystemExit, 'Could not parse the given date'):
            ProposalParser().parse_args([f'create', TEST_ACCOUNT, f'--{TEST_CLUSTER}', '100', '--end', '09/01/2500'])


class Delete(CLIAsserts, TestCase):
    """Test the ``delete`` subparsers"""

    def test_delete_proposal(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'delete {TEST_ACCOUNT} --id 0')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            ProposalParser().parse_args(['delete', '--id', '0'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            ProposalParser().parse_args(['delete', 'fake_account_name', '--id', '0'])

    def test_missing_id_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``id`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: --id'):
            ProposalParser().parse_args(['delete', TEST_ACCOUNT])


class Add(CLIAsserts, TestCase):
    """Test the ``add_sus`` subparser"""

    def test_add_sus(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'add_sus {TEST_ACCOUNT} --{TEST_CLUSTER} 100')

    def test_proposal_id(self) -> None:
        """Test a proposal ID can be specified using the ``--id`` argument"""

        self.assert_parser_matches_func_signature(
            ProposalParser(), f'add_sus {TEST_ACCOUNT} --id 0 --{TEST_CLUSTER} 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            ProposalParser().parse_args(['add_sus', f'--{TEST_CLUSTER}', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            ProposalParser().parse_args(['add_sus', 'fake_account_name', f'--{TEST_CLUSTER}', '100'])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        err_msg = 'Argument must be a non-negative integer: -100'

        # Add SUs to the active proposal, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            ProposalParser().parse_args(['add_sus', TEST_ACCOUNT, f'--{TEST_CLUSTER}', '-100'])

        # Add SUs to a specific proposal, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            ProposalParser().parse_args(['add_sus', TEST_ACCOUNT, '--id', '0', f'--{TEST_CLUSTER}', '-100'])

    def test_zero_sus(self) -> None:
        """Test zero is a valid number of service units"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'add_sus {TEST_ACCOUNT} --{TEST_CLUSTER} 0')
        self.assert_parser_matches_func_signature(ProposalParser(), f'add_sus {TEST_ACCOUNT} --id 0 --{TEST_CLUSTER} 0')


class Subtract(CLIAsserts, TestCase):
    """Test the ``subtract_sus`` subparser"""

    def test_subtract_sus(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'subtract_sus {TEST_ACCOUNT} --{TEST_CLUSTER} 100')

    def test_proposal_id(self) -> None:
        """Test a proposal ID can be specified using the ``--id`` argument"""

        self.assert_parser_matches_func_signature(
            ProposalParser(), f'subtract_sus {TEST_ACCOUNT} --id 0 --{TEST_CLUSTER} 100')

    def test_missing_account_name_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing ``account`` argument"""

        with self.assertRaisesRegex(SystemExit, 'the following arguments are required: account'):
            ProposalParser().parse_args(['subtract_sus', f'--{TEST_CLUSTER}', '100'])

    def test_nonexistent_account_error(self) -> None:
        """Test a ``SystemExit`` error is raised for a missing slurm account"""

        with self.assertRaisesRegex(SystemExit, 'No Slurm account for username'):
            ProposalParser().parse_args(['subtract_sus', 'fake_account_name', f'--{TEST_CLUSTER}', '100'])

    def test_negative_sus(self) -> None:
        """Test a ``SystemExit`` error is raised for negative service units"""

        err_msg = 'Argument must be a non-negative integer: -100'

        # Add SUs to the active proposal, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            ProposalParser().parse_args(['subtract_sus', TEST_ACCOUNT, f'--{TEST_CLUSTER}', '-100'])

        # Add SUs to a specific proposal, providing a negative SU amount
        with self.assertRaisesRegex(SystemExit, err_msg):
            ProposalParser().parse_args(['subtract_sus', TEST_ACCOUNT, '--id', '0', f'--{TEST_CLUSTER}', '-100'])

    def test_zero_sus(self) -> None:
        """Test zero is a valid number of service units"""

        self.assert_parser_matches_func_signature(ProposalParser(), f'subtract_sus {TEST_ACCOUNT} --{TEST_CLUSTER} 0')
        self.assert_parser_matches_func_signature(ProposalParser(),
                                                  f'subtract_sus {TEST_ACCOUNT} --id 0 --{TEST_CLUSTER} 0')


class Modify(CLIAsserts, TestCase):
    """Test parser arguments match the signatures of the corresponding executable"""

    def test_modify_proposal_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        date = datetime.now().strftime(settings.date_format)

        # Modify the active proposal's date, changing only the start date
        self.assert_parser_matches_func_signature(self.parser,
                                                  f'modify_date {TEST_ACCOUNT} --start {date}')

        # Modify a specific proposal's date, changing only the start date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {TEST_ACCOUNT} --ID 0 --start {date}'
        )

        # Modify the active proposal's date, changing only the end date
        self.assert_parser_matches_func_signature(self.parser, f'modify_date {TEST_ACCOUNT} --end {date}')

        # Modify a specific proposal's date, changing only the end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {TEST_ACCOUNT} --ID 0 --end {date}'
        )

        # Modify the active proposal's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {TEST_ACCOUNT} --start {date} --end {date}'
        )

        # Modify a specific proposal's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {TEST_ACCOUNT} --ID 0 --start {date} --end {date}'
        )
