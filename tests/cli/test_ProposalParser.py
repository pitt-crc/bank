from unittest import TestCase

from bank import settings
from bank.cli import ProposalParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = ProposalParser()

    def test_create_proposal(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal create --account {settings.test_account}')

    def test_delete_proposal(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal delete --account {settings.test_account}')

    def test_add_service_units(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal add --account {settings.test_account}')

    def test_subtract_service_units(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal subtract --account {settings.test_account}')

    def test_overwrite_service_units(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal overwrite --account {settings.test_account}')
