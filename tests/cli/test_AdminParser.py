from unittest import TestCase

from bank.cli import AdminParser
from tests._utils import ProposalSetup
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(ProposalSetup, CLIAsserts, TestCase):
    """Test the ``AdminParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = AdminParser()

    def test_update_status(self) -> None:
        self.assert_parser_matches_func_signature(f'admin update_status')

    def test_notify_usage(self) -> None:
        self.assert_parser_matches_func_signature(f'admin notify_usage')

    def test_run_maintenance(self) -> None:
        self.assert_parser_matches_func_signature(f'admin run_maintenance')
