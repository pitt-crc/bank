"""Wrappers around Slurm command line utilities.

API Reference
-------------
"""

from __future__ import annotations

from datetime import date
from logging import getLogger
from typing import Dict, Optional, Union, Collection, Set

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
            cmd = ShellCmd('sacctmgr --version')
            cmd.raise_if_err()

        # We catch all exceptions, but explicitly list the common cases for reference
        except (CmdError, FileNotFoundError, Exception):
            LOG.debug('Slurm is not installed.')
            return False

        LOG.debug(f'Found Slurm version "{cmd.out}"')
        return True

    @classmethod
    def cluster_names(cls) -> Set[str]:
        """Return cluster names configured with Slurm

        Returns:
            A tuple of cluster names
        """

        cmd = ShellCmd('sacctmgr show clusters format=Cluster --noheader --parsable2')
        cmd.raise_if_err()

        clusters = set(cmd.out.split())
        LOG.debug(f'Found Slurm clusters {clusters}')
        return clusters

    @staticmethod
    def partition_names(cluster: str) -> tuple[str]:
        """Return partition names within cluster configured with Slurm
        Returns:
            A tuple of partition names within the cluster specified by cluster
        """

        cmd = ShellCmd(f'sinfo -M {cluster} -o "%P" --noheader')
        cmd.raise_if_err()

        partitions = cmd.out.split()

        return partitions


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Args:
            account_name: The name of the Slurm account

        Raises:
            SystemError: If the ``sacctmgr`` utility is not installed
            AccountNotFoundError: If an account with the given name does not exist
        """

        self._account = account_name
        if not Slurm.is_installed():
            LOG.error('SystemError: Slurm is not installed')
            raise SystemError('The Slurm ``sacctmgr`` utility is not installed.')

        if not self.check_account_exists(account_name):
            LOG.error(f'AccountNotFoundError: No Slurm account for username {account_name}.')
            raise AccountNotFoundError(f'No Slurm account for username {account_name}')

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
            Whether the user is locked out on ANY of the given clusters

        Raises:
            ClusterNotFoundError: If the given slurm cluster does not exist
        """

        if cluster not in Slurm.cluster_names():
            raise ClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=GrpTresRunMins clusters={cluster}'
        return 'billing=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state: bool, cluster: str) -> None:
        """Lock or unlock the current slurm account

        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.

        Raises:
            ClusterNotFoundError: If the given slurm cluster does not exist
        """

        LOG.info(f'Updating lock state for Slurm account {self.account_name} to {lock_state}')
        if cluster not in Slurm.cluster_names():
            raise ClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        lock_state_int = 0 if lock_state else -1
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={cluster} set GrpTresRunMins=billing={lock_state_int}').raise_if_err()

    def get_cluster_usage_per_user(self, cluster: str, start: date, end: date, in_hours: bool = True) -> Dict[str, int]:
        """Return the raw account usage per user on a given cluster

        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours instead of seconds
            start: Start date to generate a report with
            end: End date to generate a report with

        Returns:
            A dictionary with the number of service units used by each user in the account

        Raises:
            ClusterNotFoundError: If the given slurm cluster does not exist
        """

        if cluster not in Slurm.cluster_names() and cluster != 'all_clusters':
            raise ClusterNotFoundError(f'Cluster {cluster} is not configured with Slurm')

        time = 'Hours'
        if not in_hours:
            time = 'Seconds'

        cmd = ShellCmd(f"sreport cluster AccountUtilizationByUser -Pn -T Billing -t {time} cluster={cluster} "
                       f"Account={self.account_name} start={start.strftime('%Y-%m-%d')} end={end.strftime('%Y-%m-%d')} format=Proper,Used")

        try:
            account_total, *data = cmd.out.split('\n')
        except ValueError:
            return None

        out_data = dict()
        for line in data:
            user, usage = line.split('|')
            usage = int(usage)
            out_data[user] = usage

        return out_data

    def get_cluster_usage_total(
        self,
        cluster: Optional[Union[str, Collection[str]]] = None,
        start = date,
        end = date,
        in_hours: bool = True) -> int:

        """Return the raw account usage total on one or more clusters

        Args:
            cluster: A string (or list of strings) of clusters to display compute a total for, default is all clusters
            in_hours: Boolean to return usage in units of hours instead of seconds

        Returns:
            The account's total usage across all of its users, across all clusters provided
        """

        if not cluster:
            clusters = settings.clusters
        else:
            clusters = (cluster, )
        # Default to all clusters in settings.clusters if not specified as an argument

        total = 0
        for cluster_name in clusters:
            user_usage = self.get_cluster_usage_per_user(cluster_name, start, end, in_hours)
            try:
                total += sum(user_usage.values())
            except AttributeError:
                # get_cluster_usage_per_user returned None because cluster was not responsive,
                # user_usage does not have values so this cluster can be skipped.
                continue

        return total

    def reset_raw_usage(self) -> None:
        """Reset the raw account usage on all clusters to zero"""

        # At the time of writing, the sacctmgr utility does not support setting
        # RawUsage to any value other than zero

        LOG.info(f'Resetting cluster usage for Slurm account {self.account_name}')
        clusters_as_str = ','.join(settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters_as_str} '
                 f'set RawUsage=0')
