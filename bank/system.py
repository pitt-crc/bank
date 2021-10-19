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
from typing import cast, Optional
from datetime import time
from email.message import EmailMessage
from functools import wraps
from logging import getLogger
from os import geteuid
from shlex import split
from smtplib import SMTP
from string import Formatter
from subprocess import PIPE, Popen
from typing import Any, Tuple

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


class EmailTemplate(Formatter):
    """A formattable email template"""

    def __init__(self, msg: str) -> None:
        self._msg = msg

    @property
    def msg(self) -> str:
        return self._msg

    @property
    def fields(self) -> Tuple[str]:
        """Return the available (unformatted) fields in the email template

        Returns:
            A tuple of unique field names
        """

        return tuple(cast(str, field_name) for _, field_name, *_ in self.parse(self.msg) if field_name is not None)

    def format(self, **kwargs) -> EmailTemplate:
        """Format the email template

        See the ``fields`` attribute for available arguments.

        Args:
            kwargs: Values used to format each field in the template
        """

        keys = set(kwargs.keys())
        incorrect_keys = keys - set(self.fields)
        if incorrect_keys:
            raise ValueError(f'Keys not found in email template: {incorrect_keys}')

        return EmailTemplate(self._msg.format(**kwargs))

    def _assert_missing_fields(self) -> None:
        """Raise an error if the template message has any unformatted fields"""

        if self.fields:
            raise RuntimeError(f'Message has unformatted fields: {self.fields}')

    def send_to(
            self, to: str, subject: str, ffrom: str = app_settings.from_address, smtp: Optional[SMTP] = None
    ) -> EmailMessage:
        """Send the email template to the given address

        Args:
            to: The email address to send the message to
            subject: The subject line of the email
            ffrom: The address of the message sender
            smtp: optionally use an existing SMTP server instance

        Returns:
            A copy of the sent email
        """

        self._assert_missing_fields()

        # Extract the text from the email
        soup = BeautifulSoup(self._msg, "html.parser")
        email_text = soup.get_text()

        msg = EmailMessage()
        msg.set_content(email_text)
        msg.add_alternative(self._msg, subtype="html")
        msg["Subject"] = subject  # f"Your allocation on H2P for account: {account.account_name}"
        msg["From"] = ffrom or app_settings.from_address
        msg["To"] = to

        with smtp or SMTP("localhost") as s:
            s.send_message(msg)

        return msg

    def __str__(self) -> str:
        return self._msg
