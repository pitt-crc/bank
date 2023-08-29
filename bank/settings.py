"""The ``settings`` module is used to define default application settings and
provides access to settings as defined in the working environment.

Application Settings
--------------------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Variable Name
     - Description
   * - test_account
     - Name of the account to use when running application tests
   * - test_cluster
     - Name of the cluster to run application tests against
   * - date_format
     - The format used when representing datetimes as strings
   * - log_path
     - The path of the application log file
   * - log_format
     - The format of log file entries (follows standard python conventions)
   * - log_level
     - The minimum severity level to include in the log file (follows standard python conventions)
   * - db_path
     - Path to the application SQLite backend
   * - clusters
     - A list of cluster names to track usage on
   * - inv_rollover_fraction
     - Fraction of service units to carry over when rolling over investments
   * - user_email_suffix
     - The email suffix for user accounts. We assume the ``Description`` field of each account in ``sacctmgr`` contains the prefix.
   * - from_address
     - The address to send user alerts from
   * - notify_levels
     - Send an email each time a user exceeds a proposal usage threshold
   * - usage_warning
     - The email template used when a user exceeds a proposal usage threshold
   * - warning_days
     - Send an email when a user's propsal is a given number of days from expiring
   * - expiration_warning
     - The email template to use when a user's propsal is a given number of days from expiring
   * - expired_proposal_notice
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
   %m/%d/%Y

Application settings are cached at import and should not be modified during
the application runtime. Likewise, modifications to environmental variables
during execution will not be recognized by the application.

.. doctest:: python

   >>> # Changing the environment during runtime
   >>> # does not affect the application settings
   >>> os.environ['BANK_DATE_FORMAT'] = '%m-%d'
   >>> print(settings.date_format)
   %m/%d/%Y
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

_CUR_DIR = Path(__file__).resolve().parent

# Settings for running the test suite.
test_accounts = ['account1', 'account2']
test_cluster = 'development'
nonexistent_account = 'fake_account'

# Define how dates should be displayed as strings (in errors, emails, and STDOUT messages)
date_format = '%m/%d/%Y'

# Where and how to write log files
log_path = "/ihome/crc/bank/crc_bank.log"
log_format = '[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
log_level = 'INFO'

# Path to the application database
db_path = "sqlite:////ihome/crc/bank/crc_bank.db"

# A list of cluster names to track usage on
clusters = ('smp', 'mpi', 'htc', 'gpu', 'teach', 'invest')

# Fraction of service units to carry over when rolling over investments
# Should be a float between 0 and 1
inv_rollover_fraction = 0.5

# The email suffix for your organization. We assume the ``Description``
# field of each account in ``sacctmgr`` contains the prefix.
user_email_suffix = '@pitt.edu'
from_address = 'noreply@pitt.edu'

# An email to send when a user has exceeded a proposal usage threshold
notify_levels = (90,)
usage_warning = dedent("""
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
    """)

# An email to send when a user is  nearing the end of their proposal
warning_days = (60,)
expiration_warning = dedent("""
    <html
    <head></head>
    <body>
    <p>
    To Whom It May Concern,<br><br>
    This email has been generated automatically because your proposal for account
    {account_name} on H2P will expire in {exp_in_days} days on {end}. 
    The one year allocation started on {start}. 
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

# An email to send when the proposal has is_expired
expired_proposal_notice = dedent("""
    <html>
    <head></head>
    <body>
    <p>
    To Whom It May Concern,<br><br>
    This email has been generated automatically because your proposal for account
    {account_name} on H2P has is_expired. The one year allocation started on {start}. 
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
