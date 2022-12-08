"""Tests for the ``AdminParser`` class"""

from argparse import ArgumentError
from unittest import TestCase

from bank.cli import AdminParser
from bank.settings import test_cluster
from tests.cli._utils import CLIAsserts


class UpdateStatus(CLIAsserts, TestCase):
    """Test the ``update_status`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'update_status')

    def test_error_on_account_name(self) -> None:
        """Test the subparser does not take additional arguments"""

        with self.assertRaises(ArgumentError):
            self.assert_parser_matches_func_signature(AdminParser(), 'update_status account1')


class ListLocked(CLIAsserts, TestCase):
    """Test the ``list_locked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_locked')

    def test_single_clusters_argument(self) -> None:
        """Test the ``--clusters`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), f'list_locked --clusters {test_cluster}')

    def test_error_invalid_cluster(self) -> None:
        """Test ``--clusters`` arguments are not valid unless defined in application settings"""

        parser = AdminParser(raise_on_error=True)
        with self.assertRaisesRegex(ArgumentError, '--clusters: invalid choice:'):
            self.assert_parser_matches_func_signature(parser, 'list_locked --clusters fake_cluster')


class ListUnlocked(CLIAsserts, TestCase):
    """Test the ``list_unlocked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_unlocked')

    def test_single_clusters_argument(self) -> None:
        """Test the ``--clusters`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_unlocked --clusters development')

    def test_error_invalid_cluster(self) -> None:
        """Test ``--clusters`` arguments are not valid unless defined in application settings"""

        parser = AdminParser(raise_on_error=True)
        with self.assertRaisesRegex(ArgumentError, '--clusters: invalid choice:'):
            self.assert_parser_matches_func_signature(parser, 'list_locked --clusters fake_cluster')
