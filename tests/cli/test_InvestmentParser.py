from datetime import datetime
from unittest import TestCase

from bank import settings
from bank.cli import InvestmentParser
from tests._utils import InvestmentSetup
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(InvestmentSetup, CLIAsserts, TestCase):
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
        date = datetime.now().strftime(settings.date_format)
        self.assert_parser_matches_func_signature(f'investment overwrite --account {settings.test_account} --id 0 --sus 10')
        self.assert_parser_matches_func_signature(f'investment overwrite --account {settings.test_account} --id 0 --start_date {date} --end_date {date}')

    def test_advance_sus(self) -> None:
        self.assert_parser_matches_func_signature(f'investment advance --account {settings.test_account} --sus 10')
