"""Tests for the ``ShellCmd`` class."""

from unittest import TestCase

from bank.exceptions import CmdError
from bank.system.slurm import ShellCmd


class InitExceptions(TestCase):
    """Tests related to exceptions raised during instantiation"""

    def test_empty_init_arg(self) -> None:
        """Test for a ``ValueError`` when the command is an empty string"""

        with self.assertRaises(ValueError):
            ShellCmd('')


class FileDescriptors(TestCase):
    """Test STDOUT and STDERR are captured and returned"""

    def test_capture_on_success(self) -> None:
        """Test for command writing to STDOUT"""

        test_message = 'hello world'
        cmd = ShellCmd(f"echo '{test_message}'")
        self.assertEqual(test_message, cmd.out)
        self.assertFalse(cmd.err)

    def test_capture_on_err(self) -> None:
        """Test for command writing to STDERR"""

        cmd = ShellCmd("ls fake_dr")
        self.assertFalse(cmd.out)
        self.assertTrue(cmd.err)

    def test_output_decoded(self) -> None:
        """Test file descriptor values are decoded"""

        cmd = ShellCmd('echo hello world')
        self.assertIsInstance(cmd.out, str)
        self.assertIsInstance(cmd.err, str)


class RaisingStdErr(TestCase):
    """Test the ``raise_if_err`` method raises appropriate errors"""

    @staticmethod
    def test_no_error_on_empty_stderr() -> None:
        """Test no error is raised for an empty STDERR output"""

        ShellCmd("echo 1").raise_if_err()

    def test_error_on_stderr_output(self) -> None:
        """Test a ``CmdError`` is raised for STDERR output"""

        with self.assertRaises(CmdError) as cm:
            ShellCmd("ls fake_dir").raise_if_err()
            self.assertEqual(str(cm.exception), "ls: cannot access 'fake_dir': No such file or directory")
