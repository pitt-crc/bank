from unittest import TestCase

from bank.cli import CLIParser


class HasSubparsers(TestCase):
    """Test the ``CLIParser`` class has all of the subparsers defined by parent classes"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cli_choices = CLIParser().add_subparsers().choices

    def test_has_admin_subparser(self) -> None:
        self.assertIn('admin', self.cli_choices)

    def test_has_slurm_subparser(self) -> None:
        self.assertIn('slurm', self.cli_choices)

    def test_has_proposal_subparser(self) -> None:
        self.assertIn('proposal', self.cli_choices)

    def test_has_investment_subparser(self) -> None:
        self.assertIn('investment', self.cli_choices)
