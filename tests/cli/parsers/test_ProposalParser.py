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
    def test_add_service_units(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active proposal, usable on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {TEST_ACCOUNT} --{settings.test_cluster} 100'
        )

        # Add SUs to a specific proposal, usable on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {TEST_ACCOUNT} --ID 0 --{settings.test_cluster} 100'
        )

        # Add SUs to the active proposal, usable across all clusters
        self.assert_parser_matches_func_signature(self.parser,
                                                  f'add_sus {TEST_ACCOUNT} --all-clusters 100')

        # Add SUs to a specific proposal, usable across all clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {TEST_ACCOUNT} --ID 0 --all-clusters 100'
        )


class Subtract(CLIAsserts, TestCase):
    def test_subtract_service_units(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        # Subtract SUs from the active proposal, removing from a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {TEST_ACCOUNT} --{settings.test_cluster} 100'
        )

        # Remove SUs from the active proposal, providing a negative SU amount
        with self.assertRaises(SystemExit):
            self.assert_parser_matches_func_signature(
                self.parser,
                f'subtract_sus {TEST_ACCOUNT} --{settings.test_cluster} -100')

        # Subtract SUs from a specific proposal, removing from a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {TEST_ACCOUNT} --ID 0 --{settings.test_cluster} 100'
        )

        # Subtract SUs from the active proposal, removing from 'all' clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {TEST_ACCOUNT} --all-clusters 100'
        )

        # Subtract SUs from a specific proposal, removing from 'all' clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {TEST_ACCOUNT} --ID 0 --all-clusters 100'
        )


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
