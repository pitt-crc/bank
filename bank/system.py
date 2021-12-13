"""The ``system`` module acts as an interface for the underlying runtime
environment and provides an object-oriented interface for interacting with
the parent system. It includes wrappers around various command line utilities
(e.g., ``sacctmgr``) and system services (e.g., ``smtp``).

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
from string import Formatter
from subprocess import PIPE, Popen
from typing import Any
from typing import Tuple, cast, Optional

from bs4 import BeautifulSoup
from environ import environ

from .exceptions import CmdError

ENV = environ.Env()
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
    """Executes commands using the underlying shell environment

    Output to StdOut and StdError from the executed command are
    written to the ``out`` and ``err`` attributes respectively.
    """

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


class EmailTemplate(Formatter):
    """A formattable email template"""

    def __init__(self, msg: str) -> None:
        """A formattable email template

        Email messages passed at innit should follow the standard python formatting syntax.
        The message can be in plain text or in HTML format.

        Args:
            msg: A partially unformatted email template
        """

        self._msg = msg

    @property
    def msg(self) -> str:
        """"The text content of the email template"""

        return self._msg

    @property
    def fields(self) -> Tuple[str]:
        """Return any unformatted fields in the email template

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

    def send_to(self, to: str, subject: str, ffrom: str, smtp: Optional[SMTP] = None) -> EmailMessage:
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
        msg["Subject"] = subject
        msg["From"] = ffrom
        msg["To"] = to

        with smtp or SMTP("localhost") as s:
            s.send_message(msg)

        return msg

    def __str__(self) -> str:
        return self._msg
