"""The ``settings`` module is used to define default application settings and
provides access to application settings as defined in the working environment.

Application Settings
--------------------

.. list-table::
   :widths: 20 25 55
   :header-rows: 1

   * - Variable Name
     - Env. Variable
     - Description
   * - test_account
     - CRC_BANK_TEST_ACCOUNT
     - Name of the account to use when running application tests
   * - test_cluster
     - CRC_BANK_TEST_CLUSTER
     - Name of the cluster to run application tests against
   * - date_format
     - CRC_BANK_DATE_FORMAT
     - The format used when representing datetimes as strings
   * - log_path
     - CRC_BANK_LOG_PATH
     - The path of the application log file
   * - log_format
     - CRC_BANK_LOG_FORMAT
     - The format of log file entries (follows standard python conventions)
   * - log_level
     - CRC_BANK_LOG_LEVEL
     - The minimum severity level to include in the log file (follows standard python conventions)
   * - db_path
     - CRC_BANK_DB_PATH
     - Path to the application SQLite backend
   * - clusters
     - CRC_BANK_CLUSTERS
     - A list of cluster names to track usage on
   * - email_suffix
     - CRC_BANK_EMAIL_SUFFIX
     - The email suffix for user accounts. We assume the ``Description`` field of each account in ``sacctmgr`` contains the prefix.
   * - from_address
     - CRC_BANK_FROM_ADDRESS
     - The address to send user alerts from
   * - notify_levels
     - CRC_BANK_NOTIFY_LEVELS
     - Send an email each time a user exceeds a proposal usage threshold
   * - usage_warning
     - CRC_BANK_USAGE_WARNING
     - The email template used when a user exceeds a proposal usage threshold
   * - warning_days
     - CRC_BANK_WARNING_DAYS
     - Send an email when a user's propsal is a given number of days from expiring
   * - expiration_warning
     - CRC_BANK_EXPIRATION_WARNING
     - The email template to use when a user's propsal is a given number of days from expiring
   * - expired_proposal_notice
     - CRC_BANK_EXPIRED_PROPOSAL_NOTICE
     - The email template to use when a user's propsal has expired

Usage Example
-------------

Application settings can be accessed as variables defined in the ``settings``
module:

.. doctest:: python

   >>> import os
   >>> from bank import settings
   >>>
   >>> # The format used by the application to represent dates as strings
   >>> print(settings.date_format)
   %m/%d/%y

Application settings are cached at import and should not be modified during
the application runtime. Likewise, modifications to environmental variables
during execution will not be recognized by the application.

.. doctest:: python

   >>> # Changing the environment during runtime
   >>> # does not affect the application settings
   >>> os.environ['BANK_DATE_FORMAT'] = '%m-%d'
   >>> print(settings.date_format)
   %m/%d/%y
"""

from __future__ import annotations

from pathlib import Path

from environ import environ

_ENV = environ.Env()
_CUR_DIR = Path(__file__).resolve().parent
_APP_PREFIX = 'BANK_'  # Prefix used to identify environmental variables as settings for this application

# Settings for running the test suite.
test_account = _ENV.get_value(_APP_PREFIX + 'TEST_ACCOUNT', default='sam')
test_cluster = _ENV.get_value(_APP_PREFIX + 'TEST_CLUSTER', default='smp')

date_format = _ENV.get_value(_APP_PREFIX + 'DATE_FORMAT', default='%m/%d/%y')

# Where and how to write log files to
log_path = _ENV.get_value(_APP_PREFIX + 'LOG_PATH', default=_CUR_DIR / 'crc_bank.log')
log_format = _ENV.get_value(_APP_PREFIX + 'LOG_FORMAT', default='[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
log_level = _ENV.get_value(_APP_PREFIX + 'LOG_LEVEL', default='INFO')

# Path to the application SQLite backend
db_path = _ENV.get_value(_APP_PREFIX + 'DB_PATH', default=f"sqlite:///{_CUR_DIR / 'crc_bank.db'}")

# A list of cluster names to track usage on
clusters = _ENV.get_value(_APP_PREFIX + 'CLUSTERS', default=('smp', 'mpi', 'gpu', 'htc'))

# The email suffix for your organization. We assume the ``Description``
# field of each account in ``sacctmgr`` contains the prefix.
email_suffix = _ENV.get_value(_APP_PREFIX + 'EMAIL_SUFFIX', default='@pitt.edu')
from_address = _ENV.get_value(_APP_PREFIX + 'FROM_ADDRESS', default='noreply@pitt.edu')

# An email to send when a user has exceeded a proposal usage threshold
notify_levels = _ENV.get_value(_APP_PREFIX + 'NOTIFY_LEVELS', default=(90,))
usage_warning = _ENV.get_value(_APP_PREFIX + 'USAGE_WARNING', default="""
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
warning_days = _ENV.get_value(_APP_PREFIX + 'WARNING_DAYS', default=(60,))
expiration_warning = _ENV.get_value(_APP_PREFIX + 'EXPIRATION_WARNING', default="""
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
expired_proposal_notice = _ENV.get_value(_APP_PREFIX + 'EXPIRED_PROPOSAL_WARNING', default="""
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
