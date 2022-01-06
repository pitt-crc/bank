from unittest import TestCase

from bank import settings
from bank.cli import AdminParser
from tests.cli._utils import CLIAsserts
from tests.dao._utils import ProposalSetup


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``AdminParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = AdminParser()

    def test_account_info(self) -> None:
        self.assert_parser_matches_func_signature(f'admin info --account {settings.test_account}')

    def test_notify_account(self) -> None:
        self.assert_parser_matches_func_signature(f'admin notify --account {settings.test_account}')

    def test_unlocked_accounts(self) -> None:
        self.assert_parser_matches_func_signature(f'admin unlocked')

    def test_renew_investment(self) -> None:
        self.assert_parser_matches_func_signature(f'admin renew --account {settings.test_account}')
