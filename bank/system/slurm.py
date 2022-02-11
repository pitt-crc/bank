"""Wrappers around the ``slurm`` command line utility.

API Reference
-------------
"""

from __future__ import annotations

from logging import getLogger

from environ import environ

from bank import settings
from bank.exceptions import CmdError, NoSuchAccountError
from .shell import ShellCmd, RequireRoot

ENV = environ.Env()
LOG = getLogger('bank.system.slurm')


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
        clusters_as_str = ','.join(settings.clusters)
        ShellCmd(
            f'sacctmgr -i modify account where account={self._account} cluster={clusters_as_str} set GrpTresRunMins=cpu={lock_state_int}'
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

    def get_total_usage(self, in_hours: bool = False) -> int:
        """Return the raw account usage across all clusters defined in application settings

        Args:
            in_hours: Return usage in units of hours (Defaults to seconds)

        Returns:
            The account's usage of the given cluster
        """

        return sum(self.get_cluster_usage(cluster, in_hours) for cluster in settings.clusters)

    @RequireRoot
    def reset_raw_usage(self) -> None:
        """Reset the raw account usage on all clusters to zero"""

        # At the time of writing, the sacctmgr utility does not support setting
        # RawUsage to any value other than zero

        LOG.info(f'Resetting cluster usage for Slurm account {self._account}')
        clusters_as_str = ','.join(settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self._account} cluster={clusters_as_str} set RawUsage=0')
