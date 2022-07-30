from datetime import datetime
from unittest import TestCase

from bank import settings
from bank.cli import ProposalSubParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):
    """Test the ``ProposalParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = ProposalSubParser()

    def test_create_proposal(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal create --account {settings.test_account}')
        self.assert_parser_matches_func_signature(f'proposal create --type Proposal --account {settings.test_account}')
        self.assert_parser_matches_func_signature(f'proposal create --type Class --account {settings.test_account}')

        self.assert_parser_matches_func_signature(f'proposal create --account {settings.test_account} --{settings.test_cluster} 100')
        self.assert_parser_matches_func_signature(f'proposal create --type Proposal --account {settings.test_account} --{settings.test_cluster} 100')
        self.assert_parser_matches_func_signature(f'proposal create --type Class --account {settings.test_account} --{settings.test_cluster} 100')

    def test_delete_proposal(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal delete --account {settings.test_account}')

    def test_add_service_units(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal add --account {settings.test_account}')

    def test_subtract_service_units(self) -> None:
        self.assert_parser_matches_func_signature(f'proposal subtract --account {settings.test_account}')

    def test_overwrite_proposal_values(self) -> None:
        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(f'proposal overwrite --account {settings.test_account}')
        self.assert_parser_matches_func_signature(f'proposal overwrite --account {settings.test_account} --{settings.test_cluster} 200')
        self.assert_parser_matches_func_signature(f'proposal overwrite --account {settings.test_account} --start {date} --end {date}')
        self.assert_parser_matches_func_signature(f'proposal overwrite --account {settings.test_account} --type Proposal')
