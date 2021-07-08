#!/usr/bin/env python
""" test.py
Usage:
    test.py email <user> <account>

Positional Arguments:
    <user>          The Pitt user to send email
    <account>       The Slurm account

Options:
    -h --help                       Print this screen and exit
"""

from docopt import docopt
import smtplib
from email.mime.text import MIMEText
from os import popen

# The magical mystical docopt line, options_first=True because su_limit_hrs can be negative!
arguments = docopt(__doc__, version='test.py version 0.0.1', options_first=True)

if True:
    email_text = """\
<html>
<head></head>
<body>
<p>
To Whom it May Concern,<br><br>
Account: {0}<br>
<pre>
{1}
</pre><br>
Thanks,<br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

# Usage command
crc_usage_command = "/ihome/crc/wrappers/crc-usage.pl {0}"
crc_usage = popen(crc_usage_command.format(arguments['<account>'])).read().strip()

# Send PI an email
From = "crc_proposal_bot@pitt.edu"
To = "{0}@pitt.edu".format(arguments['<user>'])

email = MIMEText(email_text.format(arguments['<account>'], crc_usage), 'html')

email["Subject"] = "Your allocation on H2P for account {0}".format(arguments['<account>'])
email["From"] = From
email["To"] = To

# Send the message via our own SMTP server, but don't include the
# envelope header.
s = smtplib.SMTP('localhost')
s.sendmail(From, [To], email.as_string())
s.quit()
