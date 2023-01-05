"""Tests for the ``AdminParser`` class"""

from unittest import TestCase

from bank.cli.parsers import AdminParser
from bank.settings import test_cluster
from tests.cli.parsers._utils import CLIAsserts


class UpdateStatus(CLIAsserts, TestCase):
    """Test the ``update_status`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'update_status')


class ListLocked(CLIAsserts, TestCase):
    """Test the ``list_locked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_locked')

    def test_single_clusters_argument(self) -> None:
        """Test the ``--clusters`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), f'list_locked --clusters {test_cluster}')


class ListUnlocked(CLIAsserts, TestCase):
    """Test the ``list_unlocked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_unlocked')

    def test_single_clusters_argument(self) -> None:
        """Test the ``--clusters`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), f'list_unlocked --clusters {test_cluster}')
