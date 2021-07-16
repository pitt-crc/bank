#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python
from pathlib import Path
import dataset

# define log file path as path object and check that parent directory exists
working_dir=Path(__file__).resolve().parent
log_file_path=working_dir/'logs'/'crc_bank.log'
log_file_path.parent.mkdir(exist_ok=True)

# This should contain a list of clusters you want to track usage on
CLUSTERS = ["smp", "mpi", "gpu", "htc"]

# When running the tests, uncomment the test.db line
db = dataset.connect("sqlite:////ihome/crc/bank/crc_bank.db")
# db = dataset.connect("sqlite:///test.db")

# None of these need to change
proposal_table = db["proposal"]
investor_table = db["investor"]
investor_archive_table = db["investor_archive"]
proposal_archive_table = db["proposal_archive"]
date_format = "%m/%d/%y"

# The email suffix for your organization
# We assume the Description field of sacctmgr for the account contains the prefix
email_suffix = "@pitt.edu"

# An email to send when you have exceeded a proposal threshold (25%, 50%, 75%, 90%)
# The email better contain four {}!
notify_sus_limit_email_text = """\
<html>
<head></head>
<body>
<p>
To Whom It May Concern,<br><br>
This email has been generated automatically because your account on H2P has
exceeded {}% usage. The one year allocation started on {}. You can request a
supplemental allocation at
https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br>
Your usage is printed below:<br>
<pre>
{}
</pre>
Investment status (if applicable):<br>
<pre>
{}
</pre>
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

# An email to send when you are 90 days from the end of your proposal
# The email should contain three {}!
three_month_proposal_expiry_notification_email = """\
<html>
<head></head>
<body>
<p>
To Whom It May Concern,<br><br>
This email has been generated automatically because your proposal for account
{} on H2P will expire in 90 days on {}. The one year allocation started on {}. 
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
# The email should contain two {}!
proposal_expires_notification_email = """\
<html>
<head></head>
<body>
<p>
To Whom It May Concern,<br><br>
This email has been generated automatically because your proposal for account
{} on H2P has expired. The one year allocation started on {}. You will still be
able to login and retrieve your data, but you will be unable to run new compute 
jobs until you submit a new proposal or request a supplemental allocation. 
To do so, please visit
https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines.<br><br
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""
