from __future__ import annotations

from functools import wraps
from logging import getLogger
from os import geteuid
from shlex import split
from subprocess import Popen, PIPE
from typing import Any

from environ import environ

from bank import settings
from bank.exceptions import CmdError, NoSuchAccountError

ENV = environ.Env()
LOG = getLogger('bank.system')


class RequireRoot:
    """Function decorator for requiring root privileges"""

    @staticmethod
    def check_user_is_root() -> bool:
        """Return if the current user is root"""

        return geteuid() == 0

    def __new__(cls, func: callable) -> callable:
        """Wrap the given function"""

        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            if not cls.check_user_is_root():
                LOG.error('Attempted action that requires root access without appropriate permissions')
                raise PermissionError("This action must be run with sudo privileges")

            return func(*args, **kwargs)  # pragma: no cover

        return wrapped


class ShellCmd:
    """Executes commands using the underlying shell environment

    Output to StdOut and StdError from the executed command are
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


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Args:
            account_name: The name of the slurm account

        Raises:
            SystemError: When the ``sacctmgr`` utility is not installed
            NoSuchAccountError: If the given account name does not exist
        """

        self._account = account_name
        if not self.check_slurm_installed():
            LOG.error('System error: Slurm is not installed')
            raise SystemError('The Slurm ``sacctmgr`` utility is not installed.')

        account_exists = ShellCmd(f'sacctmgr -n show assoc account={self._account}').out
        if not account_exists:
            LOG.debug(f'Could not instantiate SlurmAccount for username {account_name}. No account exists.')
            raise NoSuchAccountError(f'No Slurm account for username {account_name}')

    @property
    def account(self) -> str:
        """The name of the slurm account being administered"""

        return self._account

    @staticmethod
    def check_slurm_installed() -> bool:
        """Return whether ``sacctmgr`` is installed on the host machine"""

        try:
            cmd = ShellCmd('sacctmgr -V')
            cmd.raise_err()
            return cmd.out.startswith('slurm')

        # We catch all exceptions, but explicitly list the
        # common cases for reference by curious developers
        except (CmdError, FileNotFoundError, Exception):
            return False

    @classmethod
    @RequireRoot
    def create_account(cls, account_name: str, description: str, organization: str) -> SlurmAccount:
        """Create a new slurm account

        Args:
            account_name: The name of the slurm account
            description: The description of the account
            organization: The organization name of the account
        """

        LOG.info(f'Creating Slurm account {account_name} (description="{description}" organization="{organization}")')
        ShellCmd(
            f'sacctmgr -i add account {account_name} '
            f'description={description} '
            f'organization="{organization}" '
            f'clusters={settings.clusters_as_str}'
        ).raise_err()
        return SlurmAccount(account_name)

    @RequireRoot
    def delete_account(self) -> None:
        """Delete the slurm account"""

        ShellCmd(f"sacctmgr -i delete account {self._account} cluster={settings.clusters_as_str}").raise_err()

    @RequireRoot
    def add_user(self, user_name) -> None:
        """Add a user to the slurm account

        Args:
            user_name: The name of the user to add to the account
        """

        raise NotImplementedError()

    @RequireRoot
    def delete_user(self, user_name) -> None:
        """Delete a user from the slurm account

        Args:
            user_name: The name of the user to remove from the account
        """

        raise NotImplementedError()

    def get_locked_state(self) -> bool:
        """Return whether the user account is locked"""

        cmd = f'sacctmgr -n -P show assoc account={self._account} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out

    @RequireRoot
    def set_locked_state(self, lock_state: bool) -> None:
        """Lock or unlock the user account

        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
        """

        LOG.info(f'Updating lock state for Slurm account {self._account} to {lock_state}')
        lock_state_int = 0 if lock_state else -1
        ShellCmd(
            f'sacctmgr -i modify account where account={self._account} cluster={settings.clusters_as_str} set GrpTresRunMins=cpu={lock_state_int}'
        ).raise_err()

    def get_cluster_usage(self, cluster: str, in_hours: bool = False) -> int:
        """Return the raw account usage on a given cluster

        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours (Defaults to seconds)

        Returns:
            The account's usage of the given cluster
        """

        LOG.debug(f'Fetching cluster usage for {self._account}')

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self._account} -M {cluster} -P -a")
        header, data = cmd.out.split('\n')[1:3]
        raw_usage_index = header.split('|').index("RawUsage")
        usage = int(data.split('|')[raw_usage_index])

        if in_hours:  # Convert from seconds to hours
            usage //= 60

        return usage

    @RequireRoot
    def reset_raw_usage(self) -> None:
        """Reset the raw account usage on all clusters to zero"""

        # At the time of writing, the sacctmgr utility does not support setting
        # RawUsage to any value other than zero

        LOG.info(f'Resetting cluster usage for Slurm account {self._account}')
        ShellCmd(f'sacctmgr -i modify account where account={self._account} cluster={settings.clusters_as_str} set RawUsage=0')