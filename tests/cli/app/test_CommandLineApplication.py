"""Tests for the ``CommandLineApplication`` class"""

from unittest import TestCase

from bank.cli.app import CommandLineApplication


class HasSubparsers(TestCase):
    """Test the application parser has subparsers for each banking service"""

    @classmethod
    def setUpClass(cls) -> None:
        """Retrieve a collection of subparsers from the application"""

        cls.cli_choices = CommandLineApplication().subparsers.choices

    def test_has_admin_subparser(self) -> None:
        """Test the application parser has an ``admin`` subparser"""

        self.assertIn('admin', self.cli_choices)

    def test_has_account_subparser(self) -> None:
        """Test the application parser has an ``account`` subparser"""

        self.assertIn('account', self.cli_choices)

    def test_has_proposal_subparser(self) -> None:
        """Test the application parser has a ``proposal`` subparser"""

        self.assertIn('proposal', self.cli_choices)

    def test_has_investment_subparser(self) -> None:
        """Test the application parser has an ``investment`` subparser"""

        self.assertIn('investment', self.cli_choices)
