"""Wrappers around Slurm command line utilities.
API Reference
-------------
"""

from __future__ import annotations

from logging import getLogger
from typing import Dict

from bank import settings
from bank.exceptions import *
from bank.system.shell import ShellCmd

LOG = getLogger('bank.system.slurm')


class Slurm:
    """High level interface for Slurm commandline utilities"""

    @staticmethod
    def is_installed() -> bool:
        """Return whether ``sacctmgr`` is installed on the host machine"""

        LOG.debug('Checking for Slurm installation')

        try:
            cmd = ShellCmd('sacctmgr -V')
            cmd.raise_if_err()

        # We catch all exceptions, but explicitly list the common cases for reference
        except (CmdError, FileNotFoundError, Exception):
            LOG.debug('Slurm is not installed.')
            return False

        version = cmd.out.lstrip('slurm ')
        LOG.debug(f'Found Slurm version {version}')
        return True

    @classmethod
    def cluster_names(cls) -> tuple[str]:
        """Return cluster names configured with Slurm
        Returns:
            A tuple of cluster names
        """

        cmd = ShellCmd('sacctmgr show clusters format=Cluster  --noheader --parsable2')
        cmd.raise_if_err()

        clusters = cmd.out.split()
        LOG.debug(f'Found Slurm clusters {clusters}')
        return clusters
        
    def partition_names(cls, cluster: str) -> tuple[str]:
        """Return partition names within cluster configured with Slurm
        Returns:
            A tuple of partition names within the cluster specified by cluster
        """

        cmd = ShellCmd(f'sinfo -M {cluster} -o "%P" --noheader')
        cmd.raise_if_err()

        partitions = cmd.out.split()
        LOG.debug(f'Found Slurm partitions {clusters}')
        return partitions        


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account
        Args:
            account_name: The name of the Slurm account
        Raises:
            SystemError: If the ``sacctmgr`` utility is not installed
            SlurmAccountNotFoundError: If an account with the given name does not exist
        """

        self._account = account_name
        if not Slurm.is_installed():
            LOG.error('SystemError: Slurm is not installed')
            raise SystemError('The Slurm ``sacctmgr`` utility is not installed.')

        if not self.check_account_exists(account_name):
            LOG.error(f'SlurmAccountNotFoundError: Could not instantiate SlurmAccount for username {account_name}. No account exists.')
            raise SlurmAccountNotFoundError(f'No Slurm account for username {account_name}')

    @property
    def account_name(self) -> str:
        """The name of the Slurm account being administered"""

        return self._account

    @staticmethod
    def check_account_exists(account_name: str) -> bool:
        """Return whether the given Slurm account exists
        Args:
            account_name: The name of the Slurm account
        Returns:
            Boolean value indicating whether the account exists
        """

        cmd = ShellCmd(f'sacctmgr -n show assoc account={account_name}')
        return bool(cmd.out)

    def get_locked_state(self, cluster: str) -> bool:
        """Return whether the current slurm account is locked
        Args:
            cluster: Name of the cluster to get the lock state for
        Returns:
            Whether the user is locked out from ANY of the given clusters
        Raises:
            SlurmClusterNotFoundError: If the given slurm cluster does not exist
        """

        if cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=GrpTresRunMins clusters={cluster}'
        return 'cpu=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state: bool, cluster: str) -> None:
        """Lock or unlock the current slurm account (except for two accounts 'isenocak' and 'eschneider' with purchased partitions within gpu cluster, as speficied in update_status)
        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.
        Raises:
            SlurmClusterNotFoundError: If the given slurm cluster does not exist
        """

        LOG.info(f'Updating lock state for Slurm account {self.account_name} to {lock_state}')
        if cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        lock_state_int = 0 if lock_state else -1
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={cluster} set GrpTresRunMins=cpu={lock_state_int}').raise_if_err()
          

    def get_cluster_usage(self, cluster: str, in_hours: bool = False) -> Dict[str, int]:
        """Return the raw account usage on a given cluster
        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours instead of seconds
        Returns:
            A dictionary with the number of service units used by each user in the account
        Raises:
            SlurmClusterNotFoundError: If the given slurm cluster does not exist
        """

        if cluster and cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a -o User,RawUsage")
        header, *data = cmd.out.split('\n')[1:]

        out_data = dict()
        for line in data:
            user, usage = line.split('|')
            usage = int(usage)
            if in_hours:  # Convert from seconds to hours
                usage //= 60

            out_data[user] = usage

        return out_data

    def get_total_usage(self, in_hours: bool = True) -> int:
        """Return the raw account usage across all clusters
        Args:
            in_hours: Return usage in units of hours instead of seconds
        Returns:
            The account's usage of the given cluster
        """

        total = 0
        for cluster in settings.clusters:
            user_usage = self.get_cluster_usage(cluster, in_hours)
            total + sum(user_usage.values())

        return total

    def reset_raw_usage(self) -> None:
        """Reset the raw account usage on all clusters to zero"""

        # At the time of writing, the sacctmgr utility does not support setting
        # RawUsage to any value other than zero

        LOG.info(f'Resetting cluster usage for Slurm account {self.account_name}')
        clusters_as_str = ','.join(settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters_as_str} set RawUsage=0')
