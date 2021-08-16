from unittest import TestCase

from bank.exceptions import CmdError
from bank.utils import ShellCmd


class InitExceptions(TestCase):
    """Test appropriate errors are raised during instantiation"""

    def test_empty_init_arg(self) -> None:
        """Test for ValueError when ``cmd`` is an empty string"""

        with self.assertRaises(ValueError):
            ShellCmd('')


class FileDescriptors(TestCase):
    """Test STDOUT and STDERR are captured as attributes"""

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


class RaisingStdErr(TestCase):
    """Test the ``raise_err`` raises appropriate errors"""

    def test_no_error_on_empty_stderr(self) -> None:
        """Test no error is raised for an empty STDERR output"""

        ShellCmd("echo 1").raise_err()

    def test_no_error_on_stderr_output(self) -> None:
        """Test a ``CmdError`` is raised for STDERR output"""

        with self.assertRaises(CmdError) as cm:
            ShellCmd("ls fake_dir").raise_err()
            self.assertEqual(str(cm.exception), "ls: cannot access 'fake_dir': No such file or directory")
