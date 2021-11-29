"""The ``settings`` module defines default settings for the parent application.
It also provides access to any settings that have been overwritten using
environmental variables in the working environment.

Usage Example
-------------

The ``Defaults`` class provides access to default application settings.
Values for each setting are accessible via attributes. For example:

.. doctest:: python

   >>> from bank.settings import Defaults
   >>>
   >>> # The datetime format used when displaying or parsing dates
   >>> print(Defaults.date_format)
   %m/%d/%y

The ``Settings`` class is similar to the ``Defaults`` class, but
allows for default settings to be overwritten via environmental variables.
The ``Settings`` class should be used instead of ``Defaults`` in
most cases.

.. doctest:: python

   >>> import os
   >>> from bank.settings import Settings
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

from pathlib import Path
from typing import Any

from environ import environ

# Prefix used to identify environmental variables as settings for this application
APP_PREFIX = 'BANK_'
ENV = environ.Env()


class Settings:
    """Reflects application settings as set in the working environment"""

    def __init__(self):
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
        self.usage_warning = self._get_setting('USAGE_WARNING', """
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
            """)

        # An email to send when a user is  nearing the end of their proposal
        self.warning_days = self._get_setting('WARNING_DAYS', (60,))
        self.expiration_warning = self._get_setting('EXPIRATION_WARNING', """
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
            """)

        # An email to send when the proposal has expired
        self.expired_proposal_notice = self._get_setting('EXPIRED_PROPOSAL_WARNING', """
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
            """)

    def _get_setting(self, item: str, default) -> Any:
        return ENV.get_value(APP_PREFIX + item, cast=type(default), default=default)


app_settings = Settings()
"""An instance of the ``Settings`` class that reflects application settings as
they were defined in the working environment at package instantiation"""
