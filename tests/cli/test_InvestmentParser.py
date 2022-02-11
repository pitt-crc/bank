from unittest import TestCase

from bank import settings
from bank.cli import InvestmentParser
from tests.cli._utils import CLIAsserts
from tests.account_services._utils import InvestorSetup


class SignatureMatchesCLI(InvestorSetup, CLIAsserts, TestCase):
    """Test the ``InvestmentParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = InvestmentParser()

    def test_create_investment(self) -> None:
        self.assert_parser_matches_func_signature(f'investment create --account {settings.test_account} --sus 30')

    def test_delete_investment(self) -> None:
        self.assert_parser_matches_func_signature(f'investment delete --account {settings.test_account} --id 0')

    def test_add_sus(self) -> None:
        self.assert_parser_matches_func_signature(f'investment add --account {settings.test_account} --id 0 --sus 10')

    def test_subtract_sus(self) -> None:
        self.assert_parser_matches_func_signature(f'investment subtract --account {settings.test_account} --id 0 --sus 10')

    def test_overwrite_investment(self) -> None:
        self.assert_parser_matches_func_signature(f'investment overwrite --account {settings.test_account} --id 0 --sus 10')

    def test_advance_sus(self) -> None:
        self.assert_parser_matches_func_signature(f'investment advance --account {settings.test_account} --sus 10')
