"""Wrappers around Slurm command line utilities.

API Reference
-------------
"""

from __future__ import annotations

import re
from logging import getLogger
from typing import Dict, Optional

from bank import settings
from bank.exceptions import *
from bank.system.shell import ShellCmd

LOG = getLogger('bank.system.slurm')


class Slurm:
    """High level interface for the Slurm commandline utilities"""

    @staticmethod
    def is_installed() -> bool:
        """Return whether ``sacctmgr`` is installed on the host machine"""

        LOG.debug('Checking for Slurm installation')

        try:
            cmd = ShellCmd('sacctmgr -V')
            cmd.raise_err()

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

        # Get cluster names using squeue to fetch all running jobs for a non-existent username
        output = ShellCmd('squeue -u fakeuser -M all').out
        regex_pattern = re.compile(r'CLUSTER: (.*)\n')
        regex_match = re.findall(regex_pattern, output)
        clusters = tuple(set(regex_match))

        LOG.debug(f'Found Slurm clusters {clusters}')
        return clusters


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Args:
            account_name: The name of the Slurm account

        Raises:
            SystemError: When the ``sacctmgr`` utility is not installed
            SlurmAccountNotFoundError: If the given account name does not exist
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

    def get_locked_state(self, cluster: Optional[str]) -> bool:
        """Return whether the user account is locked

        Args:
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.

        Returns:
            Whether the user is locked out from ANY of the given clusters
        """

        if cluster and cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        if cluster is None:
            cluster = ','.join(Slurm.cluster_names())

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=GrpTresRunMins clusters={cluster}'
        return 'cpu=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state: bool, cluster: Optional[str]) -> None:
        """Lock or unlock the user account

        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.
        """

        LOG.info(f'Updating lock state for Slurm account {self.account_name} to {lock_state}')
        if cluster and cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        if cluster is None:
            cluster = ','.join(Slurm.cluster_names())

        lock_state_int = 0 if lock_state else -1
        ShellCmd(
            f'sacctmgr -i modify account where account={self.account_name} cluster={cluster} set GrpTresRunMins=cpu={lock_state_int}'
        ).raise_err()

    def get_cluster_usage(self, cluster: str, in_hours: bool = False) -> Dict[str, int]:
        """Return the raw account usage on a given cluster

        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours instead of seconds

        Returns:
            A dictionary with the number of service units used by each user in the account
        """

        if cluster and cluster not in Slurm.cluster_names():
            raise SlurmClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        header, *data = cmd.out.split('\n')[1:]
        raw_usage_index = header.split('|').index("RawUsage")
        username_index = header.split('|').index("User")

        out_data = dict()
        for line in data:
            split_line = line.split('|')
            user = split_line[username_index]
            usage = int(split_line[raw_usage_index])
            if in_hours:  # Convert from seconds to hours
                usage //= 60

            out_data[user] = usage

        return out_data

    def get_total_usage(self, in_hours: bool = True) -> int:
        """Return the raw account usage across all clusters defined in application settings

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
