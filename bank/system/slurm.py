"""Wrappers around the ``slurm`` command line utility.

API Reference
-------------
"""

from __future__ import annotations

import re
from logging import getLogger
from typing import Dict, Optional

from environ import environ

from bank import settings
from bank.exceptions import CmdError, SlurmAccountNotFoundError, SlurmAccountExistsError
from . import ldap
from .shell import ShellCmd

ENV = environ.Env()
LOG = getLogger('bank.system.slurm')


class Slurm:
    """High level interface for the suite of slurm commandline utilities"""

    @staticmethod
    def is_installed() -> bool:
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
    def cluster_names(cls) -> tuple[str]:
        """Return cluster names configured with slurm

        Returns:
            A tuple of cluster names
        """

        # Get cluster names using squeue to fetch all running jobs for a non-existent username
        output = ShellCmd('squeue -u fakeuser -M all').out
        regex_pattern = re.compile(r'CLUSTER: (.*)\n')
        return tuple(set(re.findall(regex_pattern, output)))


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Args:
            account_name: The name of the slurm account

        Raises:
            SystemError: When the ``sacctmgr`` utility is not installed
            SlurmAccountNotFoundError: If the given account name does not exist
        """

        self._account = account_name
        if not Slurm.is_installed():
            LOG.error('System error: Slurm is not installed')
            raise SystemError('The Slurm ``sacctmgr`` utility is not installed.')

        if not self.check_account_exists(account_name):
            LOG.debug(f'Could not instantiate SlurmAccount for username {account_name}. No account exists.')
            raise SlurmAccountNotFoundError(f'No Slurm account for username {account_name}')

    def __repr__(self) -> str:
        return self._account

    @property
    def account_name(self) -> str:
        """The name of the slurm account being administered"""

        return self._account

    @staticmethod
    def check_account_exists(account_name: str) -> bool:
        """Return whether the given slurm account exists

        Args:
            account_name: The name of the slurm account

        Returns:
            Boolean value indicating whether the account exists
        """

        cmd = ShellCmd(f'sacctmgr -n show assoc account={account_name}')
        return bool(cmd.out)

    @classmethod
    def create_account(cls, account_name: str, description: str, organization: str) -> SlurmAccount:
        """Create a new slurm account

        Args:
            account_name: The name of the new Slurm account
            description: Description of the new slurm user account
            organization: Internal organization or department of the slurm user account

        Returns:
            An instance of the parent class for the new user account
        """

        ldap.check_ldap_user(description)
        if cls.check_account_exists(account_name):
            raise SlurmAccountExistsError(f'Account {account_name} already exists')

        clus_str = ','.join(settings.clusters)
        ShellCmd(
            f'sacctmgr -i add account {account_name} description="{description}" organization="{organization}" clusters={clus_str}'
        ).raise_err()

        return SlurmAccount(account_name)

    def delete_account(self) -> None:
        """Delete the current Slurm account"""

        clus_str = ','.join(settings.clusters)
        ShellCmd(f"sacctmgr -i delete account {self} cluster={clus_str}").raise_err()

    def add_user(self, user: str, make_default: bool = False) -> None:
        """Add a new user to the current slurm account

        Args:
            user: Name of the user to add to the current account
            make_default: Make the current account the default account for the user

        Raises:
            LdapUserNotFound: If the given user does not exist in LDAP
            LdapUserNotFound: If the current account is not a group in LDAP
        """

        ldap.check_ldap_user(user, raise_if_false=True)
        ldap.check_ldap_group(self.account_name, raise_if_false=True)

        if not make_default:
            ShellCmd(f"sacctmgr -i add user {user} account={self} cluster=smp,gpu,mpi,htc").raise_err()

        if ldap.check_crc_user(user):
            ShellCmd(
                f"sacctmgr -i update user where user={user} cluster=smp,gpu,mpi,htc set defaultaccount={self}"
            )

        else:
            ShellCmd(
                f"sacctmgr -i add user {user} defaultaccount={self} cluster=smp,gpu,mpi,htc"
            )

    def remove_user(self, user: str) -> None:
        """Remove an existing user from the current Slurm account

        Args:
            user: Name of the user to remove from the current account
        """

        ldap.check_ldap_user(user, raise_if_false=True)
        clus_str = ','.join(settings.clusters)
        ShellCmd(f"sacctmgr -i delete user {user} account={self} cluster={clus_str}").raise_err()

    def get_locked_state(self, cluster: Optional[str]) -> bool:
        """Return whether the user account is locked

        Args:
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.

        Returns:
            Whether the user is locked out from ANY of the given clusters
        """

        if cluster is None:
            cluster = ','.join(Slurm.cluster_names())

        cmd = f'sacctmgr -n -P show assoc account={self} format=grptresrunmins clusters={cluster}'
        return 'cpu=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state: bool, cluster: Optional[str]) -> None:
        """Lock or unlock the user account

        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
            cluster: Name of the cluster to get the lock state for. Defaults to all clusters.
        """

        LOG.info(f'Updating lock state for Slurm account {self} to {lock_state}')
        lock_state_int = 0 if lock_state else -1
        if cluster is None:
            cluster = ','.join(Slurm.cluster_names())

        ShellCmd(
            f'sacctmgr -i modify account where account={self} cluster={cluster} set GrpTresRunMins=cpu={lock_state_int}'
        ).raise_err()

    def get_cluster_usage(self, cluster: str, in_hours: bool = False) -> Dict[str, int]:
        """Return the raw account usage on a given cluster

        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours instead of seconds

        Returns:
            A dictionary with the number of service units used by each user in the account
        """

        LOG.debug(f'Fetching cluster usage for {self}')

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self} -M {cluster} -P -a")
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

        LOG.info(f'Resetting cluster usage for Slurm account {self}')
        clusters_as_str = ','.join(settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self} cluster={clusters_as_str} set RawUsage=0')
