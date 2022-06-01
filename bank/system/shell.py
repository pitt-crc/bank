"""Wrappers around the underlying runtime shell.

API Reference
-------------
"""

from functools import wraps
from logging import getLogger
from os import geteuid
from shlex import split
from subprocess import Popen, PIPE

from bank.exceptions import CmdError

LOG = getLogger('bank.system.shell')


class RequireRoot:
    """Function decorator for requiring root privileges"""

    @staticmethod
    def check_user_is_root() -> bool:
        """Return if the current user is root"""

        return geteuid() == 0

    def __new__(cls, func: callable) -> callable:
        """Wrap the given function"""

        @wraps(func)
        def wrapped(*args, **kwargs):
            if not cls.check_user_is_root():
                LOG.error('Attempted action that requires root access without appropriate permissions')
                raise PermissionError("This action must be run with sudo privileges")

            return func(*args, **kwargs)  # pragma: no cover

        return wrapped


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

    def raise_err(self) -> None:
        """Raise an exception if the piped command wrote to STDERR

        Raises:
            CmdError: If there is an error output
        """

        if self.err:
            LOG.debug(f'Shell command errored out with message: {self.err} ')
            raise CmdError(self.err)
