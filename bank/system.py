"""The ``system`` module acts as an interface for the underlying runtime
environment and provides general utilities for interacting with the parent system.
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

The ``Settings`` class provides access to application settings as instance
attributes. Setting values can be overwritten via environmental variables.

.. doctest:: python

   >>> import os
   >>> from bank.system import Settings
   >>>
   >>> # Specify the date format as an environmental variable
   >>> os.environ['BANK_DATE_FORMAT'] = '%m-%d-%y'
   >>>
   >>> settings = Settings()
   >>> print(settings.date_format)
   %m-%d-%y


API Reference
-------------
"""

from __future__ import annotations

from email.message import EmailMessage
from functools import wraps
from logging import getLogger
from os import geteuid
from pathlib import Path
from shlex import split
from smtplib import SMTP
from string import Formatter
from subprocess import PIPE, Popen
from typing import Any
from typing import Tuple, cast, Optional

from bs4 import BeautifulSoup
from environ import environ

from .exceptions import CmdError

# Prefix used to identify environmental variables as settings for this application
ENV = environ.Env()
APP_PREFIX = 'BANK_'
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


class Settings:
    """Reflects application settings as set in the working environment"""

    def __init__(self) -> None:
        self.test_account = self._get_setting('TEST_ACCOUNT', 'sam')
        self.test_cluster = self._get_setting('TEST_CLUSTER', 'smp')
        self.date_format = self._get_setting('DATE_FORMAT', '%m/%d/%y')

        # Where and how to write log files to
        _application_dir = Path(__file__).resolve().parent
        self.log_path = self._get_setting('LOG_PATH', _application_dir / 'crc_bank.log')
        self.log_format = self._get_setting('LOG_FORMAT', '[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
        self.log_level = self._get_setting('LOG_LEVEL', 'INFO')

        # Path to the application SQLite backend
        self.db_path = self._get_setting('DB_PATH', f"sqlite:///{_application_dir / 'crc_bank.db'}")

        # A list of cluster names to track usage on
        self.clusters = self._get_setting('CLUSTERS', ('smp', 'mpi', 'gpu', 'htc'))

        # The email suffix for your organization. We assume the ``Description``
        # field of each account in ``sacctmgr`` contains the prefix.
        self.email_suffix = self._get_setting('EMAIL_SUFFIX', '@pitt.edu')
        self.from_address = self._get_setting('FROM_ADDRESS', 'noreply@pitt.edu')

        # The email templates below accept the following formatting fields:
        #   account: The account name
        #   start_date: The start date of the proposal
        #   end_date: The end date of the proposal
        #   usage: Tabular summary of the proposal's service unit usage
        #   perc: Usage percentage threshold that triggered the message being sent
        #   investment: Tabular summary of user's current usage on invested machines
        #   exp_in_days: Number of days until proposal expires

        # An email to send when a user has exceeded a proposal usage threshold
        self.notify_levels = self._get_setting('NOTIFY_LEVELS', (90,))
        self.usage_warning = self._get_setting('USAGE_WARNING', EmailTemplate("""
            <html>
            <head></head>
            <body>
            <p>
            To Whom It May Concern,<br><br>
            This email has been generated automatically because your account on H2P has
            exceeded {perc}% usage. The one year allocation started on {start_date}. You can 
            request a supplemental allocation at
            https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br>
            Your usage is printed below:<br>
            <pre>
            {usage}
            </pre>
            Investment status (if applicable):<br>
            <pre>
            {investment}
            </pre>
            Thanks,<br><br>
            The CRC Proposal Bot
            </p>
            </body>
            </html>
            """))

        # An email to send when a user is  nearing the end of their proposal
        self.warning_days = self._get_setting('WARNING_DAYS', (60,))
        self.expiration_warning = self._get_setting('EXPIRATION_WARNING', EmailTemplate("""
            <html>
            <head></head>
            <body>
            <p>
            To Whom It May Concern,<br><br>
            This email has been generated automatically because your proposal for account
            {account_name} on H2P will expire in {exp_in_days} days on {end_date}. 
            The one year allocation started on {start_date}. 
            Once your proposal expires, you will still be able to login and retrieve your 
            data, but you will be unable to run new compute jobs until you submit a new 
            proposal or request a supplemental allocation.
            To do so, please visit
            https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br
            Thanks,<br><br>
            The CRC Proposal Bot
            </p>
            </body>
            </html>
            """))

        # An email to send when the proposal has expired
        self.expired_proposal_notice = self._get_setting('EXPIRED_PROPOSAL_WARNING', EmailTemplate("""
            <html>
            <head></head>
            <body>
            <p>
            To Whom It May Concern,<br><br>
            This email has been generated automatically because your proposal for account
            {account} on H2P has expired. The one year allocation started on {start_date}. 
            You will still be able to login and retrieve your data, but you will be unable
            to run new compute  jobs until you submit a new proposal or request a 
            supplemental allocation. To do so, please visit
            https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br
            Thanks,<br><br>
            The CRC Proposal Bot
            </p>
            </body>
            </html>
            """))

    def _get_setting(self, item: str, default) -> Any:
        return ENV.get_value(APP_PREFIX + item, cast=type(default), default=default)


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
