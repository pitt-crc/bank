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

from environ.environ import Env

# Prefix used to identify environmental variables as settings for this application
APP_PREFIX = 'BANK_'


class Defaults:
    """Default settings for the parent application"""

    is_testing = False
    date_format = "%m/%d/%y"

    # Where and how to write log files to
    _application_dir = Path(__file__).resolve().parent
    log_path = _application_dir / 'crc_bank.log'
    log_format = '[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
    log_level = 'INFO'

    # Path to the application SQLite backend
    db_path = f'sqlite:///{_application_dir / "crc_bank.db"}'
    db_test_path = f'sqlite:///{_application_dir / "test.db"}'

    # A list of cluster names to track usage on
    clusters = ("smp", "mpi", "gpu", "htc")

    # The email suffix for your organization. We assume the ``Description``
    # field of each account in ``sacctmgr`` contains the prefix.
    email_suffix = "@pitt.edu"
    from_address = "noreply@pitt.edu"

    # The email templates below accept the following formatting fields:
    #   account: The account name
    #   start: The start date of the proposal
    #   expire: The end date of the proposal
    #   usage: Tabular summary of the proposal's service unit usage
    #   perc: Usage percentage threshold that triggered the message being sent
    #   investment: Tabular summary of user's current usage on invested machines

    # An email to send when you have exceeded a proposal threshold
    notify_levels = (25, 50, 75, 90)
    notify_sus_limit_email_text = """\
    <html>
    <head></head>
    <body>
    <p>
    To Whom It May Concern,<br><br>
    This email has been generated automatically because your account on H2P has
    exceeded {perc}% usage. The one year allocation started on {start}. You can 
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
    """

    # An email to send when you are 90 days from the end of your proposal
    three_month_proposal_expiry_notification_email = """\
    <html>
    <head></head>
    <body>
    <p>
    To Whom It May Concern,<br><br>
    This email has been generated automatically because your proposal for account
    {account} on H2P will expire in 90 days on {expire}. The one year allocation started on {start}. 
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
    """

    # An email to send when the proposal has expired
    proposal_expires_notification_email = """\
    <html>
    <head></head>
    <body>
    <p>
    To Whom It May Concern,<br><br>
    This email has been generated automatically because your proposal for account
    {account} on H2P has expired. The one year allocation started on {start}. 
    You will still be able to login and retrieve your data, but you will be unable
    to run new compute  jobs until you submit a new proposal or request a 
    supplemental allocation. To do so, please visit
    https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br
    Thanks,<br><br>
    The CRC Proposal Bot
    </p>
    </body>
    </html>
    """


class Settings:
    """Reflects application settings as set in the working environment"""

    def __init__(self) -> None:
        """Application settings as defined in the parent environment."""
        self._env = Env()

    def __getattribute__(self, item: str) -> Any:
        default = getattr(Defaults, item)
        env_key = APP_PREFIX + item.upper()
        env = object.__getattribute__(self, '_env')
        return env.get_value(env_key, cast=type(default), default=default)


app_settings = Settings()
"""An instance of the ``Settings`` class that reflects application settings as
they were defined in the working environment at package instantiation"""
