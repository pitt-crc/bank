"""The ``utils`` module provides general utilities for the parent application"""

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

    @staticmethod
    def require_root_access() -> None:
        """Raise an error if the current session does not have root permissions

        Raises:
            RuntimeError: If session is not root
        """

        if geteuid() != 0:
            raise RuntimeError("This action must be run with sudo privileges")

    def __new__(cls, func: callable) -> callable:
        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            cls.require_root_access()
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

    def __init__(self, acount_name: str) -> None:
        self.account_name = acount_name

    def get_locked_state(self):
        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out

    def set_locked_state(self, lock_state):
        lock_state_int = 0 if lock_state else -1
        clusters = ','.join(app_settings.clusters)
        ShellCmd(
            f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'
        ).raise_err()

    def _raw_cluster_usage(self, cluster: str, in_hours: bool = False) -> int:
        """Return the account usage on a given cluster in seconds"""

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        header, data = cmd.out.split('\n')[1:3]
        raw_usage_index = header.split('|').index("RawUsage")
        usage = data.split('|')[raw_usage_index]

        if in_hours:  # Convert from seconds to hours
            usage = time(second=usage).hour

        return usage

    def raw_cluster_usage(self, in_hours=False):
        return {c: self._raw_cluster_usage(c, in_hours=in_hours) for c in app_settings.clusters}

    def reset_raw_usage(self):
        clusters = ','.join(app_settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set RawUsage=0')


def check_service_units_valid(units):
    """Return a proper natural number as a ``Right`` instance
    
    Args:
        units: Actual service units used as a parameter

    Returns:
        The passed value as an instance of ``Right``

    Raises:
        ValueError: If the input ``units`` is not a natural number
    """

    if units <= 0:
        raise ValueError(f"SUs must be greater than or equal to zero, got `{units}`")


def check_service_units_valid_clusters(sus, greater_than_ten_thousand=True):
    for clus, val in sus.items():
        try:
            sus[clus] = int(val)

        except ValueError:
            raise ValueError(f"Given non-integer value `{val}` for cluster `{clus}`")

    total_sus = sum(sus.values())
    if greater_than_ten_thousand and total_sus < 10000:
        raise ValueError(f"Total SUs should exceed 10000 SUs, got `{total_sus}`")

    elif total_sus <= 0:
        raise ValueError(f"Total SUs should be greater than zero, got `{total_sus}`")


def find_next_notification(usage):
    members = app_settings.notify_levels
    exceeded = [usage > x.to_percentage() for x in members]

    try:
        index = exceeded.index(False)
        result = 0 if index == 0 else members[index - 1]

    except ValueError:
        result = 100

    return result


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
