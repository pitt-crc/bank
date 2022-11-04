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
    def test_slurm_is_installed(self, *args) -> None:
        """Test slurm registers as being installed in the test environment"""

        self.assertTrue(Slurm.is_installed())

    @patch('bank.system.shell.ShellCmd._subprocess_call', return_value=('', 'command not found'))
    def test_slurm_not_installed(self, *args) -> None:
        """Test slurm registers as being installed in the test environment"""

        self.assertFalse(Slurm.is_installed())
