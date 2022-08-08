"""Tests for the ``ProposalParser`` class"""

from datetime import datetime
from unittest import TestCase

from bank import settings
from bank.cli import ProposalParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):
    """Test parser arguments match the signatures of the corresponding executable"""

    def setUp(self) -> None:
        """Define an instance of the parser object being tested"""

        self.parser = ProposalParser()

    def test_create_proposal(self) -> None:
        """Test the parsing of arguments by the ``create`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            'create {settings.test_account}')
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --{settings.test_cluster} 100')
        self.assert_parser_matches_func_signature(
            self.parser,
            f'create {settings.test_account} --all 100')

    def test_add_service_units(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            'add {settings.test_account} --{settings.test_cluster} 100')
        self.assert_parser_matches_func_signature(
            self.parser,
            f'add {settings.test_account} --all 100')

    def test_subtract_service_units(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(
            self.parser,
            'subtract {settings.test_account} --{settings.test_cluster} 100')
        self.assert_parser_matches_func_signature(
            self.parser,
            f'subtract {settings.test_account} --all 100')


    def test_modify_proposal_date(self) -> None:
        """Test the parsing of arguments by the ``modify_date`` command"""

        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(
            self.parser,
            f'modify_date {settings.test_account} --start {date} --end {date}')
