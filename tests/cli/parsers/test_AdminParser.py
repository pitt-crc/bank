"""Tests for the ``AdminParser`` class"""

from unittest import TestCase

from bank import settings
from bank.cli.parsers import AdminParser
from bank.settings import test_cluster
from tests.cli.parsers._utils import CLIAsserts

TEST_CLUSTER = settings.test_cluster


class UpdateStatus(CLIAsserts, TestCase):
    """Test the ``update_status`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call is valid without any additional arguments"""

        self.assert_parser_matches_func_signature(AdminParser(), 'update_status')

    def test_error_on_account_name(self) -> None:
        """Test a ``SystemExit`` error is raised if an account name is provided"""

        with self.assertRaisesRegex(SystemExit, 'unrecognized arguments'):
            AdminParser().parse_args(['update_status', 'account1'])


class ListLocked(CLIAsserts, TestCase):
    """Test the ``list_locked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call exits when additional arguments are not supplied"""

        with self.assertRaises(SystemExit):
            AdminParser().parse_args(['list_locked'])

    def test_single_clusters_argument(self) -> None:
        """Test the ``--cluster`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), f'list_locked --cluster {test_cluster}')

        # Test the clusters are parsed into the `cluster` attribute
        args = AdminParser().parse_args(['list_locked', '--cluster', TEST_CLUSTER])
        self.assertCountEqual(TEST_CLUSTER, args.cluster)

    def test_error_invalid_cluster(self) -> None:
        """Test ``--cluster`` arguments are not valid unless defined in application settings"""

        with self.assertRaisesRegex(SystemExit, '--cluster: invalid choice:'):
            AdminParser().parse_args(['list_locked', '--cluster', 'fake_cluster'])


class ListUnlocked(CLIAsserts, TestCase):
    """Test the ``list_unlocked`` subparser"""

    def test_no_arguments(self) -> None:
        """Test the subparser call exits when additional arguments are not supplied"""

        with self.assertRaises(SystemExit):
            AdminParser().parse_args(['list_unlocked'])

    def test_single_clusters_argument(self) -> None:
        """Test the ``--cluster`` argument accepts at least one cluster name"""

        self.assert_parser_matches_func_signature(AdminParser(), 'list_unlocked --cluster development')

        # Test the clusters are parsed into the `cluster` attribute
        args = AdminParser().parse_args(['list_unlocked', '--cluster', TEST_CLUSTER])
        self.assertCountEqual(TEST_CLUSTER, args.cluster)

    def test_error_invalid_cluster(self) -> None:
        """Test ``--cluster`` arguments are not valid unless defined in application settings"""

        with self.assertRaisesRegex(SystemExit, '--cluster: invalid choice:'):
            AdminParser().parse_args(['list_locked', '--cluster', 'fake_cluster'])
