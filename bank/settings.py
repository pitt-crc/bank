"""Application settings for the bank monitoring system"""

from pathlib import Path
from typing import Any

from environ.environ import Env

# Prefix used to identify env variables as settings for this application
APP_PREFIX = 'BANK_'


class Defaults:
    """Default settings for the parent application"""

    is_testing = False
    date_format = "%m/%d/%y"

    # Where and how to write log files to
    _application_dir = Path(__file__).resolve().parent
    log_path = _application_dir / 'logs' / 'crc_bank.log'
    log_format = '[%(asctime)s] %(levelname)s - %(message)s'
    log_level = 'INFO'

    # Path to the application SQLite backend
    db_path = _application_dir / 'crc_bank.db'
    db_test_path = _application_dir / 'test.db'

    # A list of cluster names to track usage on
    clusters = ["smp", "mpi", "gpu", "htc"]

    # The email suffix for your organization. We assume the ``Description``
    # field of each account in ``sacctmgr`` contains the prefix.
    email_suffix = "@pitt.edu"

    # The email templates below accept the following formatting fields:
    #   account: The account name
    #   start: The start date of the proposal
    #   expire: The end date of the proposal
    #   usage: Tabular summary of the proposal's service unit usage
    #   perc: Usage percentage threshold that triggered the message being sent
    #   investment: Tabular summary of user's current usage on invested machines

    # An email to send when you have exceeded a proposal threshold (25%, 50%, 75%, 90%)
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


class Settings(Defaults):
    """Reflects application settings as set in the working environment"""

    def __getattribute__(self, item: str) -> Any:
        default = getattr(super(), item)
        env_key = APP_PREFIX + item.upper()
        return Env().get_value(env_key, cast=type(default), default=default)


# Provided a prebuilt ``Settings`` instance as a
# dedicated entry point to application settings
app_settings = Settings()
Path(app_settings.log_path).parent.mkdir(exist_ok=True)
