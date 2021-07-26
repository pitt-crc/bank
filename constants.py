"""Configuration file for the CRC bank monitoring system"""

from pathlib import Path

import dataset
import environ

# -- System information ------------------------------------------------------

# Where to write log files to
parent_dir = Path(__file__).resolve().parent
log_file_path = parent_dir / 'logs' / 'crc_bank.log'  # Path to the log file

# Path to the application SQLite database (must be an absolute path)
db_path = f"sqlite:///{parent_dir / 'test.db'}"

# This should contain a list of clusters you want to track usage on
CLUSTERS = ["smp", "mpi", "gpu", "htc"]

# -- Email notification Settings ---------------------------------------------

# The email suffix for your organization. We assume the ``Description`` field
# of each account in ``sacctmgr`` contains the prefix.
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

# DO NOT CHANGE BELOW THIS LINE
# -----------------------------
env = environ.Env()
db_path = env.str('CRC_BANK_DB', default=db_path)
clusters = env.list('CRC_BANK_CLUSTERS', default=CLUSTERS)
log_file_path = env.str('CRC_BANK_LOG', default=log_file_path)

db = dataset.connect(db_path)
proposal_table = db["proposal"]
investor_table = db["investor"]
investor_archive_table = db["investor_archive"]
proposal_archive_table = db["proposal_archive"]
date_format = "%m/%d/%y"

Path(log_file_path).parent.mkdir(exist_ok=True)
