#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python

from __future__ import annotations

from email.message import EmailMessage
from enum import Enum
from functools import wraps
from logging import getLogger
from os import geteuid
from pathlib import Path
from shlex import split
from smtplib import SMTP
from subprocess import PIPE, Popen
from typing import Any, List

import datafreeze
from bs4 import BeautifulSoup

from .exceptions import CmdError

LOG = getLogger('bank.utils')


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

    def __new__(self, func: callable) -> callable:
        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            self.require_root_access()
            return func(*args, **kwargs)

        return wrapped


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
    members = list(PercentNotified)
    exceeded = [usage > x.to_percentage() for x in members]

    try:
        index = exceeded.index(False)
        result = PercentNotified.Zero if index == 0 else members[index - 1]

    except ValueError:
        result = PercentNotified.Hundred

    return result


class PercentNotified(Enum):
    Zero = 0
    TwentyFive = 1
    Fifty = 2
    SeventyFive = 3
    Ninety = 4
    Hundred = 5

    def succ(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        if index >= len(members):
            return members[0]
        else:
            return members[index]

    def pred(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) - 1
        if index < 0:
            return members[5]
        else:
            return members[index]

    def to_percentage(self):
        if self == PercentNotified.Zero:
            return 0.0
        elif self == PercentNotified.TwentyFive:
            return 25.0
        elif self == PercentNotified.Fifty:
            return 50.0
        elif self == PercentNotified.SeventyFive:
            return 75.0
        elif self == PercentNotified.Ninety:
            return 90.0
        else:
            return 100.0


class ProposalType(Enum):
    Proposal = 0
    Class = 1
    Investor = 2

    @classmethod
    def from_string(cls, name: str) -> ProposalType:
        try:
            return cls(getattr(cls, name.title()))

        except AttributeError:
            raise ValueError(f'Invalid proposal type: `{name}`')


def freeze_if_not_empty(items: List, path: Path):
    force_eval = [dict(p) for p in items]
    if force_eval:
        datafreeze.freeze(force_eval, format="json", filename=path)
    else:
        with open(path, "w") as f:
            f.write("{}\n")


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
