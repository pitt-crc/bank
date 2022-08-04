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

        self.assert_parser_matches_func_signature(self.parser, 'create --account dummy_user')
        self.assert_parser_matches_func_signature(self.parser, f'create --account dummy_user --{settings.test_cluster} 100')

    def test_delete_proposal(self) -> None:
        """Test the parsing of arguments by the ``delete`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'delete --account dummy_user')

    def test_add_service_units(self) -> None:
        """Test the parsing of arguments by the ``add`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'add --account dummy_user')

    def test_subtract_service_units(self) -> None:
        """Test the parsing of arguments by the ``subtract`` command"""

        self.assert_parser_matches_func_signature(self.parser, 'subtract --account dummy_user')

    def test_overwrite_proposal_values(self) -> None:
        """Test the parsing of arguments by the ``overwrite`` command"""

        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(self.parser, 'overwrite --account dummy_user')
        self.assert_parser_matches_func_signature(self.parser, f'overwrite --account dummy_user --{settings.test_cluster} 200')
        self.assert_parser_matches_func_signature(self.parser, f'overwrite --account dummy_user --start {date} --end {date}')
