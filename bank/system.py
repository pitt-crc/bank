"""Interface for the underlying runtime environment.

The ``system`` module provides general utilities for interfacing with the
underlying runtime environment. It includes common administrative tasks in
addition to wrappers around various command line utilities.
"""

from __future__ import annotations

from datetime import time
from email.message import EmailMessage
from functools import wraps
from logging import getLogger
from os import geteuid
from shlex import split
from smtplib import SMTP
from subprocess import PIPE, Popen
from typing import Any

from bs4 import BeautifulSoup

from .exceptions import CmdError
from .settings import app_settings

LOG = getLogger('bank.utils')


class RequireRoot:
    """Function decorator for requiring root privileges"""

    def __new__(cls, func: callable) -> callable:
        """Wrap the given function"""

        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            if geteuid() != 0:
                raise PermissionError("This action must be run with sudo privileges")

            return func(*args, **kwargs)

        return wrapped


class ShellCmd:
    """Executes commands using the underlying command line environment"""

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
            raise CmdError(self.err)


class SlurmAccount:
    """Common administrative tasks relating to Slurm user accounts"""

    def __init__(self, account_name: str) -> None:
        """A Slurm user account

        Provides python wrappers around common Slurm administrative tasks
        typically performed using the ``sacctmgr`` and ``sshare`` command line
        utilities.

        Args:
            account_name: The name of the user account
        """

        self.account_name = account_name

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

    def cluster_usage(self, cluster: str, in_hours: bool = False) -> int:
        """Return the account usage on a given cluster

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
        usage = data.split('|')[raw_usage_index]

        if in_hours:  # Convert from seconds to hours
            usage = time(second=usage).hour

        return usage

    def reset_raw_usage(self) -> None:
        """Reset the current account usage"""

        clusters = ','.join(app_settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set RawUsage=0')


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
