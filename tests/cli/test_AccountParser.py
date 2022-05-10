from unittest import TestCase

from bank import settings
from bank.cli import AdminParser, AccountParser
from tests.cli._utils import CLIAsserts
from tests._utils import ProposalSetup


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``AccountParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = AccountParser()

    def test_account_info(self) -> None:
        self.assert_parser_matches_func_signature(f'account info --account {settings.test_account}')

    def test_lock(self) -> None:
        self.assert_parser_matches_func_signature(f'account lock --account {settings.test_account}')

    def test_unlock(self) -> None:
        self.assert_parser_matches_func_signature(f'account unlock --account {settings.test_account}')

    def test_renew_investment(self) -> None:
        self.assert_parser_matches_func_signature(f'account renew --account {settings.test_account}')
