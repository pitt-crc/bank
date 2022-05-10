from unittest import TestCase

from bank import settings
from bank.cli import AdminParser
from tests.cli._utils import CLIAsserts
from tests._utils import ProposalSetup


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``AdminParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = AdminParser()

    def test_notify_account(self) -> None:
        self.assert_parser_matches_func_signature(f'admin lock_expired')

    def test_unlocked_accounts(self) -> None:
        self.assert_parser_matches_func_signature(f'admin find_unlocked')
