"""Tests for the ``ProposalParser`` class"""

from datetime import datetime
from unittest import TestCase, skipIf

from bank import settings
from bank.cli import ProposalParser
from bank.system import Slurm
from tests.cli._utils import CLIAsserts


@skipIf(not Slurm.is_installed(), 'Slurm is not installed on this machine')
class SignatureMatchesCLI(TestCase, CLIAsserts):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = ProposalParser()

    def test_create_proposal(self) -> None:
        """Test the parsing of arguments by the ``create`` command"""

        # Create a proposal with default values
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account}')

        # Create proposal, adding SUs to a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --{settings.test_cluster} 100'
        )

        # Create a proposal, adding SUs to 'all' clusters
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --all_clusters 100')

        # Create a proposal, specifying a start date
        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --start {date} ')

        # Create a proposal, specifying a duration
        self.assert_parser_matches_func_signature(self.parser, f'create {settings.test_account} --duration 6')

    def test_add_service_units(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        # Add SUs to the active proposal, usable on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {settings.test_account} --{settings.test_cluster} 100'
        )

        # Add SUs to a specific proposal, usable on a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {settings.test_account} --ID 0 --{settings.test_cluster} 100'
        )

        # Add SUs to the active proposal, usable across all clusters
        self.assert_parser_matches_func_signature(self.parser, f'add_sus {settings.test_account} --all_clusters 100')

        # Add SUs to a specific proposal, usable across all clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add_sus {settings.test_account} --ID 0 --all_clusters 100'
        )

    def test_subtract_service_units(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        # Subtract SUs from the active proposal, removing from a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {settings.test_account} --{settings.test_cluster} 100'
        )

        # Subtract SUs from a specific proposal, removing from a specific cluster
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {settings.test_account} --ID 0 --{settings.test_cluster} 100'
        )

        # Subtract SUs from the active proposal, removing from 'all' clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {settings.test_account} --all_clusters 100'
        )

        # Subtract SUs from a specific proposal, removing from 'all' clusters
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract_sus {settings.test_account} --ID 0 --all_clusters 100'
        )

    def test_modify_proposal_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        date = datetime.now().strftime(settings.date_format)

        # Modify the active proposal's date, changing only the start date
        self.assert_parser_matches_func_signature(self.parser, f'modify_date {settings.test_account} --start {date}')

        # Modify a specific proposal's date, changing only the start date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date}'
        )

        # Modify the active proposal's date, changing only the end date
        self.assert_parser_matches_func_signature(self.parser, f'modify_date {settings.test_account} --end {date}')

        # Modify a specific proposal's date, changing only the end date
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --end {date}'
        )

        # Modify the active proposal's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --start {date} --end {date}'
        )

        # Modify a specific proposal's date, changing the start and end dates
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --ID 0 --start {date} --end {date}'
        )
