"""Wrappers around the underlying runtime shell.

API Reference
-------------
"""

from logging import getLogger
from shlex import split
from subprocess import PIPE, Popen
from typing import List, Tuple

from bank.exceptions import CmdError

LOG = getLogger('bank.system.shell')


class ShellCmd:
    """Execute commands using the underlying shell

    Outputs to STDOUT and STDERR are exposed via the ``out`` and ``err``
    attributes respectively.
    """

    def __init__(self, cmd: str) -> None:
        """Execute the given command in the underlying shell

        Args:
            cmd: The command to run

        Raises:
            ValueError: When the ``cmd`` argument is empty
        """

        if not cmd.split():
            raise ValueError('Command string cannot be empty')

        LOG.debug(f'executing `{cmd}`')
        self.out, self.err = self._subprocess_call(split(cmd))

    @staticmethod
    def _subprocess_call(args: List[str]) -> Tuple[str, str]:
        """Wrapper method for executing shell commands via ``Popen.communicate``

        Args:
            args: A sequence of program arguments

        Returns:
            The piped output to STDOUT and STDERR as strings
        """

        out, err = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
        out = out.decode("utf-8").strip()
        err = err.decode("utf-8").strip()
        return out, err

    def raise_if_err(self) -> None:
        """Raise an exception if the piped command wrote to STDERR

        Raises:
            CmdError: If there is an error output
        """

        if self.err:
            LOG.error(f'CmdError: Shell command errored out with message: {self.err}')
            raise CmdError(self.err)
