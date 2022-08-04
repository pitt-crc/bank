"""Wrappers around the underlying runtime shell.

API Reference
-------------
"""

from logging import getLogger
from shlex import split
from subprocess import Popen, PIPE

from bank.exceptions import CmdError

LOG = getLogger('bank.system.shell')


class ShellCmd:
    """Executes commands using the underlying shell environment

    Output to STDOUT and STDERR from the executed command are
    written to the ``out`` and ``err`` attributes respectively.
    """

    def __init__(self, cmd: str) -> None:
        """Execute the given command in the underlying shell

        Args:
            cmd: The command to be run in a new pipe
        """

        if not cmd:
            raise ValueError('Command string cannot be empty')

        LOG.debug(f'executing `{cmd}`')
        out, err = Popen(split(cmd), stdout=PIPE, stderr=PIPE).communicate()
        self.out = out.decode("utf-8").strip()
        self.err = err.decode("utf-8").strip()

    def raise_if_err(self) -> None:
        """Raise an exception if the piped command wrote to STDERR

        Raises:
            CmdError: If there is an error output
        """

        if self.err:
            LOG.debug(f'CmdError: Shell command errored out with message: {self.err} ')
            raise CmdError(self.err)
