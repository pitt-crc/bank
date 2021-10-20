"""The ``system`` module acts as an interface for the underlying system shell
and provides general utilities for interacting with the runtime environment.
It includes wrappers around various command line utilities (e.g., ``sacctmgr``)
and system services (e.g., ``smtp``).

Usage Example
-------------

.. doctest:: python

   >>> from bank import system
   >>>
   >>> # Run a shell command
   >>> cmd = system.ShellCmd("echo 'Hello World'")
   >>> print(cmd.out)
   Hello World

   >>> # Require root permissions for a function
   >>> @system.RequireRoot
   ... def foo():
   ...     print('This function requires root access')

API Reference
-------------
"""

from __future__ import annotations

from email.message import EmailMessage
from functools import wraps
from logging import getLogger
from os import geteuid
from shlex import split
from smtplib import SMTP
from subprocess import PIPE, Popen
from typing import Any

from bs4 import BeautifulSoup

from .exceptions import CmdError, NoSuchAccountError
from .settings import app_settings

LOG = getLogger('bank.utils')


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
                raise PermissionError("This action must be run with sudo privileges")

            return func(*args, **kwargs)  # pragma: no cover

        return wrapped


class ShellCmd:
    """Executes commands using the underlying shell environment"""

    def __init__(self, cmd: str) -> None:
        """Execute the given command in the underlying shell

        Output to StdOut and StdError from the executed command are
        written to the ``out`` and ``err`` attributes respectively.

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
            raise CmdError(self.err)


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Args:
            account_name: The name of the user account
        """

        self.account_name = account_name
        if not self.check_slurm_installed():
            raise SystemError('The Slurm ``sacctmgr`` utility is not installed.')

        account_exists = ShellCmd(f'sacctmgr -n show assoc account={self.account_name}').out
        if not account_exists:
            raise NoSuchAccountError(f'No Slurm account for username {account_name}')

    @staticmethod
    def check_slurm_installed() -> bool:
        """Return whether sacctmgr is installed on the host machine"""

        try:
            cmd = ShellCmd('sacctmgr -V')
            cmd.raise_err()
            return cmd.out.startswith('slurm')

        except (CmdError, FileNotFoundError, Exception):
            return False

    def get_locked_state(self) -> bool:
        """Return whether the user account is locked

        Returns:
            The account lock state as a boolean
        """

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state: bool) -> False:
        """Lock or unlock the user account

        Args:
            lock_state: Whether to lock (``True``) or unlock (``False``) the user account
        """

        lock_state_int = 0 if lock_state else -1
        clusters = ','.join(app_settings.clusters)
        ShellCmd(
            f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'
        ).raise_err()

    def get_cluster_usage(self, cluster: str, in_hours: bool = False) -> int:
        """Return the raw account usage on a given cluster

        Args:
            cluster: The name of the cluster
            in_hours: Return usage in units of hours (Defaults to seconds)

        Returns:
            The account's usage of the given cluster
        """

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        header, data = cmd.out.split('\n')[1:3]
        raw_usage_index = header.split('|').index("RawUsage")
        usage = int(data.split('|')[raw_usage_index])

        if in_hours:  # Convert from seconds to hours
            usage //= 60

        return usage

    def set_raw_usage(self, usage: int, *cluster: str) -> None:
        """Set the raw account usage on a given cluster

        Args:
            *cluster: The name of the cluster
            usage: The usage value to set in units of seconds"""

        clus = ','.join(cluster)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clus} set RawUsage={usage}')

    def reset_raw_usage(self) -> None:
        """Reset the raw account usage on all clusters to zero"""

        self.set_raw_usage(0, *app_settings.clusters)


def send_email(account, email_html: str) -> None:
    """Send an email to a user account

    Args:
        account: The account to send an email to
        email_html: The content of the email
    """

    # Extract the text from the email
    soup = BeautifulSoup(email_html, "html.parser")
    email_text = soup.get_text()

    msg = EmailMessage()
    msg.set_content(email_text)
    msg.add_alternative(email_html, subtype="html")
    msg["Subject"] = f"Your allocation on H2P for account: {account.account_name}"
    msg["From"] = "noreply@pitt.edu"
    msg["To"] = account.get_email_address()

    with SMTP("localhost") as s:
        s.send_message(msg)
