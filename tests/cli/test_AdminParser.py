from unittest import TestCase

from bank import settings
from bank.cli import AdminParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = AdminParser()

    def test_account_info(self) -> None:
        self.assert_parser_matches_func_signature(f'admin info --account={settings.test_account}')

    def test_notify_account(self) -> None:
        self.assert_parser_matches_func_signature(f'admin notify --account={settings.test_account}')

    def test_unlocked_accounts(self) -> None:
        self.assert_parser_matches_func_signature(f'admin unlocked')
