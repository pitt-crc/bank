from unittest import TestCase

from bank import settings
from bank.cli import SlurmParser
from tests.cli._utils import CLIAsserts


class SignatureMatchesCLI(TestCase, CLIAsserts):

    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = SlurmParser()

    def test_add_account(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm add_acc --account {settings.test_account}')

    def test_delete_account(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm delete_acc --account {settings.test_account}')

    def test_add_user(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm add_user --account {settings.test_account} --user fake_user')

    def test_delete_user(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm delete_user --account {settings.test_account} --user fake_user')

    def test_lock(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm lock --account {settings.test_account}')

    def test_unlock(self) -> None:
        self.assert_parser_matches_func_signature(f'slurm unlock --account {settings.test_account}')
