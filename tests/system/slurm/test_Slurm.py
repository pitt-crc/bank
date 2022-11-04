"""Tests for the ``Slurm`` class."""

from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.system.slurm import Slurm


class ClusterNames(TestCase):
    """Tests for the ``cluster_names`` method"""

    def test_names_match_test_env(self) -> None:
        """Test returned cluster names match the clusters configured in the test environment"""

        self.assertEqual(Slurm.cluster_names(), {settings.test_cluster, })


class IsInstalled(TestCase):
    """Tests for the ``is_installed`` method"""

    @patch('bank.system.shell.ShellCmd._subprocess_call', return_value=('slurm 0.0.0', ''))
    def test_is_installed_true(self, *args) -> None:
        """Test the return value is ``True`` when slurm is installed"""

        self.assertTrue(Slurm.is_installed())

    @patch('bank.system.shell.ShellCmd._subprocess_call', return_value=('', 'command not found'))
    def test_not_installed_false(self, *args) -> None:
        """Test the return value is ``False`` when slurm is not installed"""

        self.assertFalse(Slurm.is_installed())

    def test_installed_in_test_env(self) -> None:
        """Test slurm is installed in the test environment"""

        self.assertTrue(Slurm.is_installed())
