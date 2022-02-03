from unittest import TestCase

from bank import settings
from bank.cli import SlurmParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):
    """Test the ``SlurmParser`` interface defines arguments that match the underlying DAO signatures"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = SlurmParser()

    def test_lock(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm lock --account {settings.test_account}')

    def test_unlock(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm unlock --account {settings.test_account}')
