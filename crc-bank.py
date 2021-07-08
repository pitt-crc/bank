#!/usr/bin/env python
''' crc-bank.py -- Deal with crc-bank.db
Usage:
    crc-bank.py insert <account> <su_limit_hrs>
    crc-bank.py modify <account> <su_limit_hrs>
    crc-bank.py add <account> <su_limit_hrs>
    crc-bank.py change <account> <su_limit_hrs>
    crc-bank.py get_sus <account> 
    crc-bank.py check_service_units_limit <account> 
    crc-bank.py check_end_of_date_limit <account> 
    crc-bank.py reset_usage <account> 
    crc-bank.py release_hold <account> 
    crc-bank.py three_month_check <account> 
    crc-bank.py dump <filename>
    crc-bank.py repopulate <filename>
    crc-bank.py info <account>
    crc-bank.py remove <account>
    crc-bank.py modify_proposal_date <account> <date>
    crc-bank.py alloc_sus
    crc-bank.py -h | --help
    crc-bank.py -v | --version

Positional Arguments:
    <account>       The Slurm account
    <su_limit_hrs>  The limit in CPU Hours (e.g. 10,000)
    <filename>      Dump to or repopulate from file, format is JSON
    <date>          Changes proposal beginning date (e.g 01/01/18)

Options:
    -h --help                       Print this screen and exit
    -v --version                    Print the version of crc-bank.py

Examples:
    crc-bank.py insert # insert for the first time
    crc-bank.py modify # change to a new limit, modifies proposal date
    crc-bank.py add    # add SUs on top of current value
    crc-bank.py change # change to a new limit, don't change proposal date
'''


# Test:
# 1. Is the number of service units really an integer?
# 2. Is the number of service units greater than the default?
def check_service_units(given_integer):
    try:
        service_units = int(given_integer)
        if service_units == -1:
            print("WARNING: Giving the group infinite SUs")
        elif service_units < 10000:
            exit("ERROR: Number of SUs => {0} is too small!".format(service_units))
        return service_units
    except ValueError:
        exit("ERROR: The given limit => {0} is not an integer!".format(given_integer))


# Test:
# 1. Does association for account and all clusters exists in Slurm database?
def check_account_and_cluster(account):
    for cluster in ['smp', 'gpu', 'mpi', 'htc']:
        command = "sacctmgr -n show assoc account={0} cluster={1} format=account,cluster"
        check_string = popen(command.format(account, cluster)).read().split('\n')[0]
        if check_string.strip() == "":
            exit("ERROR: no association for account {0} on cluster {1}".format(account, cluster))


# Test:
# 1. On insert, does item already exist in the database?
def check_insert_item_in_table(table, account):
    if not table.find_one(account=account) is None:
        exit("ERROR: Account {0} already exists in database, did you want to modify it?".format(account))

# Test:
# 1. On modify, make sure item exists
def check_item_in_table(table, account, mode):
    if table.find_one(account=account) is None:
        if mode == 'modify' or mode == 'check':
            exit("ERROR: Account {0} doesn't exists in database, did you want to insert it?".format(account))
        elif mode == 'reset_usage':
            exit("ERROR: Account {0} doesn't exists in database, you should create a limit before resetting?".format(account))


# Logging function
def log_action(string):
    #with open('logs/crc-bank.log', 'a+') as f:
    with open('/ihome/crc/bank/logs/crc-bank.log', 'a+') as f:
        f.write("{0}: {1}\n".format(datetime.now(), string))


import dataset
from docopt import docopt
# Default is python 2.6, can't use subprocess
from os import popen, geteuid
from os.path import exists
from datetime import date, datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import json
import sys

# The magical mystical docopt line, options_first=True because su_limit_hrs can be negative!
arguments = docopt(__doc__, version='crc-bank.py version 0.0.1', options_first=True)

# Check account and cluster associations actually exist
# -> these won't exist for dump or repopulate
if not (arguments['dump'] or arguments['repopulate'] or arguments['alloc_sus'] or arguments["remove"]):
    check_account_and_cluster(arguments['<account>'])

# Connect to the database and get the limits table
# Absolute path ////
db = dataset.connect('sqlite:////ihome/crc/bank/crc-bank.db')
# Relative path ///
#db = dataset.connect('sqlite:///crc-bank.db')
table = db['crc']

# For each insert/update/check, do operations
if arguments['insert']:
    # Check that Slurm account exists
    check_account_and_cluster(arguments['<account>'])

    # Check if database item already exists
    check_insert_item_in_table(table, arguments['<account>'])

    # Check <su_limit_hrs>
    service_units = check_service_units(arguments['<su_limit_hrs>']) 

    # Insert the limit
    table.insert(dict(account=arguments['<account>'], su_limit_hrs=service_units,
                 date=date.today(), percent_informed=False, half_percent_informed=False, limit_informed=False))

    # Log the action
    log_action("Account: {0} Insert: {1}".format(arguments['<account>'], service_units))

elif arguments['modify']:
    # Does the user have root?
    if geteuid() != 0:
        exit("ERROR: modify must be run with sudo privelage")

    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'modify')

    # Get the usage from `sshare` for the account and cluster
    command = "sshare --noheader --account={0} --cluster={1} --format=RawUsage"
    raw_usage = 0
    for cluster in ['smp', 'gpu', 'mpi', 'htc']:
        raw_usage += int(popen(command.format(arguments['<account>'], cluster)).read().split('\n')[1].strip())

    # raw usage is in CPU Seconds
    raw_usage /= (60 * 60)

    # Get limit in database
    limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']

    # Compute SUs thrown away
    thrown_away = limit - raw_usage
    log_action("Account: {0} threw away {1} SUs".format(arguments['<account>'], thrown_away))

    # Check <su_limit_hrs>
    service_units = check_service_units(arguments['<su_limit_hrs>']) 

    # Modify the limit
    table.update(dict(account=arguments['<account>'], su_limit_hrs=service_units,
                 date=date.today(), percent_informed=False, half_percent_informed=False, limit_informed=False), ['account'])

    # Reset sshare usage
    command = "sacctmgr -i modify account where account={0} cluster=smp,gpu,mpi,htc set RawUsage=0"
    popen(command.format(arguments['<account>']))

    # Log the action
    log_action("Account: {0} Modify: {1}".format(arguments['<account>'], service_units))

elif arguments['change']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'modify')

    # Check <su_limit_hrs>
    service_units = check_service_units(arguments['<su_limit_hrs>']) 

    # Modify the limit
    table.update(dict(account=arguments['<account>'], su_limit_hrs=service_units,
                      percent_informed=False, half_percent_informed=False, limit_informed=False), ['account'])

    # Log the action
    log_action("Account: {0} Change: {1}".format(arguments['<account>'], service_units))

elif arguments['add']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'modify')

    # Check <su_limit_hrs>
    service_units = check_service_units(arguments['<su_limit_hrs>']) 
    service_units += table.find_one(account=arguments['<account>'])['su_limit_hrs']

    # Modify the limit, but not the date
    table.update(dict(account=arguments['<account>'], su_limit_hrs=service_units,
                 percent_informed=False, half_percent_informed=False, limit_informed=False), ['account'])

    # Log the action
    log_action("Account: {0} Add, New Limit: {1}".format(arguments['<account>'], service_units))

elif arguments['check_service_units_limit']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Get the usage from `sshare` for the account on each cluster
    command = "sshare --noheader --account={0} --cluster={1} --format=RawUsage"
    raw_usage = 0
    for cluster in ['smp', 'gpu', 'mpi', 'htc']:
        raw_usage += int(popen(command.format(arguments['<account>'], cluster)).read().split('\n')[1].strip())

    # raw usage is in CPU Seconds
    raw_usage /= (60 * 60)

    # Get limit in database
    limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']

    # Check for 90% usage, send email
    if limit == 0 or limit == -1:
        percent = 0
    else:
        percent = 100 * int(raw_usage) / limit

    # If the limit is -1 the usage is unlimited
    if limit != -1 and int(raw_usage) > limit:
        # Account reached limit, set hold on account
        command = "sacctmgr -i modify account where account={0} cluster=smp,gpu,mpi,htc set GrpTresRunMins=cpu=0"
        popen(command.format(arguments['<account>']))

        if limit != 0:
            informed = table.find_one(account=arguments['<account>'])['limit_informed']
            if not informed:
                email_text = """\
<html>
<head></head>
<body>
<p>
To Whom it May Concern,<br><br>
This email has been generated automatically because your allocation for account
{0} on H2P has run out of SUs! The one-year allocation started on {1}. To submit a proposal see
https://crc.pitt.edu/apply for more details. If you need supplemental SUs
please see https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines. The output of `crc-usage.pl {0}`
is printed below:<br>
<pre>
{2}
<pre><br>
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

                # Get the account usage
                crc_usage_command = "/ihome/crc/wrappers/crc-usage.pl {0}"
                crc_usage = popen(crc_usage_command.format(arguments['<account>'])).read().strip()

                # Send PI an email
                From = "crc_proposal_bot@pitt.edu"
                command = "sacctmgr -n list account account={0} format=description"
                pittusername = popen(command.format(arguments['<account>'])).read().strip()
                To = "{0}@pitt.edu".format(pittusername)

                begin_date = table.find_one(account=arguments['<account>'])['date']

                email = MIMEText(email_text.format(arguments['<account>'], begin_date, crc_usage), "html")

                email["Subject"] = "Your allocation on H2P for account {0}".format(arguments['<account>'])
                email["From"] = From
                email["To"] = To

                # Send the message via our own SMTP server, but don't include the
                # envelope header.
                s = smtplib.SMTP('localhost')
                s.sendmail(From, [To], email.as_string())
                s.quit()

                # Log the action
                log_action("Account: {0} Held".format(arguments['<account>']))

                # PI has been informed
                table.update(dict(account=arguments['<account>'], limit_informed=True),
                            ['account'])

    elif limit != -1 and percent >= 90:
        informed = table.find_one(account=arguments['<account>'])['percent_informed']
        if not informed:
            # Account is close to limit, inform PI
            email_text = """\
<html>
<head></head>
<body>
<p>
To Whom it May Concern,<br><br>
This email has been generated automatically because your allocation on H2P for
account {0} is at {1}% usage. The one-year allocation started on {2}. To submit
a proposal see https://crc.pitt.edu/apply for more details. If you need
supplemental SUs please see https://crc.pitt.edu/Pitt-CRC-Allocation-Proposal-Guidelines. The
output of `crc-usage.pl {0}` is printed below:<br>
<pre>
{3}
<pre><br>
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

            # Get the account usage
            crc_usage_command = "/ihome/crc/wrappers/crc-usage.pl {0}"
            crc_usage = popen(crc_usage_command.format(arguments['<account>'])).read().strip()

            # Send PI an email
            From = "crc_proposal_bot@pitt.edu"
            command = "sacctmgr -n list account account={0} format=description"
            pittusername = popen(command.format(arguments['<account>'])).read().strip()
            To = "{0}@pitt.edu".format(pittusername)

            begin_date = table.find_one(account=arguments['<account>'])['date']

            email = MIMEText(email_text.format(arguments['<account>'], percent, begin_date, crc_usage), "html")

            email["Subject"] = "Your allocation on H2P for account {0}".format(arguments['<account>'])
            email["From"] = From
            email["To"] = To

            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('localhost')
            s.sendmail(From, [To], email.as_string())
            s.quit()

            # PI has been informed
            table.update(dict(account=arguments['<account>'], percent_informed=True),
                        ['account'])

    elif limit != -1 and percent >= 50:
        informed = table.find_one(account=arguments['<account>'])['half_percent_informed']
        if not informed:
            # Account is close to limit, inform PI
            email_text = """\
<html>
<head></head>
<body>
<p>
To Whom it May Concern,<br><br>
This email has been generated automatically because your allocation on H2P for
account {0} is at {1}% usage. The one-year allocation started on {2}. To submit
a proposal see https://crc.pitt.edu/apply for more details. The output from
`crc-usage.pl {0}` is printed below:<br>
<pre>
{3}
</pre>
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

            # Get the account usage
            crc_usage_command = "/ihome/crc/wrappers/crc-usage.pl {0}"
            crc_usage = popen(crc_usage_command.format(arguments['<account>'])).read().strip()

            # Send PI an email
            From = "crc_proposal_bot@pitt.edu"
            command = "sacctmgr -n list account account={0} format=description"
            pittusername = popen(command.format(arguments['<account>'])).read().strip()
            To = "{0}@pitt.edu".format(pittusername)

            begin_date = table.find_one(account=arguments['<account>'])['date']

            email = MIMEText(email_text.format(arguments['<account>'], percent, begin_date, crc_usage), "html")

            email["Subject"] = "Your allocation on H2P for account {0}".format(arguments['<account>'])
            email["From"] = From
            email["To"] = To

            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('localhost')
            s.sendmail(From, [To], email.as_string())
            s.quit()

            # PI has been informed
            table.update(dict(account=arguments['<account>'], half_percent_informed=True),
                        ['account'])

elif arguments['reset_usage']:
    # Does the user have root?
    if geteuid() != 0:
        exit("ERROR: reset_usage must be run with sudo privelage")

    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'reset_usage')

    # Reset sshare usage
    command = "sacctmgr -i modify account where account={0} cluster=smp,gpu,mpi,htc set RawUsage=0"
    popen(command.format(arguments['<account>']))

    # Update the date in the database
    table.update(dict(account=arguments['<account>'], date=date.today(), percent_informed=False, half_percent_informed=False, limit_informed=False), ['account'])

    # Log the action
    log_action("Account: {0} Reset".format(arguments['<account>']))

elif arguments['check_end_of_date_limit']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Check date is 366 or more days from previous
    db_date = table.find_one(account=arguments['<account>'])['date']
    current_date = date.today()
    comparison_days = current_date - db_date

    if comparison_days.days > 365:
        # If the usage was unlimited, just update the date otherwise set to 10K
        limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']
        if limit == -1 or limit == 0:
            table.update(dict(account=arguments['<account>'], date=date.today(), percent_informed=False, half_percent_informed=False, limit_informed=False),
                        ['account'])

            # Log the action
            log_action("Account: {0} End of Date Update".format(arguments['<account>']))
        else:
            # Get the usage from `sshare` for the account and cluster
            command = "sshare --noheader --account={0} --cluster={1} --format=RawUsage"
            raw_usage = 0
            for cluster in ['smp', 'gpu', 'mpi', 'htc']:
                raw_usage += int(popen(command.format(arguments['<account>'], cluster)).read().split('\n')[1].strip())

            # raw usage is in CPU Seconds
            raw_usage /= (60 * 60)

            # Get limit in database
            limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']

            # Compute SUs thrown away
            thrown_away = limit - raw_usage
            log_action("Account: {0} threw away {1} SUs".format(arguments['<account>'], thrown_away))

            table.update(dict(account=arguments['<account>'], su_limit_hrs=10000,
                        date=date.today(), percent_informed=False, half_percent_informed=False, limit_informed=False), ['account'])
            log_action("Account: {0} End of Date Reset".format(arguments['<account>']))

        # Reset raw usage
        command = "sacctmgr -i modify account where account={0} cluster=smp,gpu,mpi,htc set RawUsage=0"
        popen(command.format(arguments['<account>']))

elif arguments['get_sus']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Print out SUs
    string = "Account {0} on H2P has {1} SUs"
    sus = table.find_one(account=arguments['<account>'])['su_limit_hrs']
    print(string.format(arguments['<account>'], sus))

elif arguments['release_hold']:
    # Does the user have root?
    if geteuid() != 0:
        exit("ERROR: release_hold must be run with sudo privelage")

    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Get the usage from `sshare` for the account and cluster
    command = "sshare --noheader --account={0} --cluster={1} --format=RawUsage"
    raw_usage = 0
    for cluster in ['smp', 'gpu', 'mpi', 'htc']:
        raw_usage += int(popen(command.format(arguments['<account>'], cluster)).read().split('\n')[1].strip())

    # raw usage is in CPU Seconds
    raw_usage /= (60 * 60)

    # Get limit in database
    limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']
    
    # Make sure raw usage is less than limit
    if int(raw_usage) < limit:
        # Account reached limit, remove hold on account
        command = "sacctmgr -i modify account where account={0} cluster=smp,gpu,mpi,htc set GrpTresRunMins=cpu=-1"
        popen(command.format(arguments['<account>']))

        # Log the action
        log_action("Account: {0} Released Hold".format(arguments['<account>']))
    else:
        exit("ERROR: The raw usage on the account is larger than the limit... you'll need to add SUs")

elif arguments['three_month_check']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Get today's date and end_date from table
    today = date.today()
    begin_date = table.find_one(account=arguments['<account>'])['date']

    # End date is the begin_date + 365 days
    end_date = begin_date + timedelta(365)
    delta = end_date - today
    
    # Make sure limit isn't 0 or -1
    limit = table.find_one(account=arguments['<account>'])['su_limit_hrs']

    # If the dates are separated by 90 days and the limits aren't 0 or -1 send an email
    if delta.days == 90 and limit != -1:
        email_text = """
<html>
<head></head>
<body>
<p>
To Whom it May Concern,<br><br>
This email has been generated automatically 90 days before your proposal on
cluster H2P will reset for account {0}. On {1}, 10K SUs will be added to your
account. You must submit a
proposal at least 2 weeks prior to either January 1st, April 1st, July 1st, or
October 1st based on your proposal's end date ({1}). To submit your new
proposal see https://crc.pitt.edu/apply for more details. The output from `crc-usage.pl {0}`
is printed below:<br>
<pre>
{2}
</pre><br>
Thanks,<br><br>
The CRC Proposal Bot
</p>
</body>
</html>
"""

        # Get the account usage
        crc_usage_command = "/ihome/crc/wrappers/crc-usage.pl {0}"
        crc_usage = popen(crc_usage_command.format(arguments['<account>'])).read().strip()

        # Send PI an email
        From = "crc_proposal_bot@pitt.edu"
        command = "sacctmgr -n list account account={0} format=description"
        pittusername = popen(command.format(arguments['<account>'])).read().strip()
        To = "{0}@pitt.edu".format(pittusername)
        email = MIMEText(email_text.format(arguments['<account>'], end_date, crc_usage), "html")

        email["Subject"] = "Your allocation on H2P for account {0}".format(arguments['<account>'])
        email["From"] = From
        email["To"] = To

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        s = smtplib.SMTP('localhost')
        s.sendmail(From, [To], email.as_string())
        s.quit()

elif arguments['dump']:        
    if not exists(arguments['<filename>']):
        items = db['crc'].all()
        dataset.freeze(items, format='json', filename=arguments['<filename>'])
    else:
        exit("ERROR: file {0} exists, don't want you to overwrite a backup".format(arguments['<filename>']))

elif arguments['remove']:        
    print("DANGER: This function will remove {0} from the crc-bank.db, are you sure? [y/N]".format(arguments['<account>']))
    if sys.version_info >= (3, 0):
        choice = input().lower()
    else:
        choice = raw_input().lower()
    if choice == "yes" or choice == "y":
        # Check if database item exists
        check_item_in_table(table, arguments['<account>'], 'check')

        # Item exists, delete it
        table.delete(account=arguments['<account>'])

        # Log the action
        log_action("Account: {0} Remove".format(arguments['<account>']))

elif arguments['repopulate']:
    if exists(arguments['<filename>']):
        print("DANGER: This function OVERWRITES crc-bank.db, are you sure you want to do this? [y/N]")
        choice = raw_input().lower()
        if choice == "yes" or choice == "y":
            # Get the contents
            contents = json.load(open(arguments['<filename>']))
            
            # Drop the current table and recreate it
            table.drop()
            table = db['crc']
            
            # Fix the contents['results'] list of dicts
            for item in contents['results']:
                # Python 2.6 doesn't support a read from string for dates
                str_to_int = [int(x) for x in item['date'].split('-')]
                item['date'] = date(str_to_int[0], str_to_int[1], str_to_int[2])
                item['su_limit_hrs'] = int(item['su_limit_hrs'])

            # Insert the list                
            table.insert_many(contents['results'])
    else:
        exit("ERROR: file {0} doesn't exist? Can't repopulate from nothing".format(arguments['<filename>']))

elif arguments['info']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Print out information
    for key, value in table.find_one(account=arguments['<account>']).items():
        try:
            print("{:>22} {:>16}".format(key, value.strftime("%m/%d/%y")))
        except AttributeError:
            print("{:>22} {:>16}".format(key, value))

elif arguments['modify_proposal_date']:
    # Check if database item exists
    check_item_in_table(table, arguments['<account>'], 'check')

    # Can we actually parse the date
    correct_date = datetime.strptime(arguments['<date>'], '%m/%d/%y')
    
    # Update the account with the beginning date
    table.update(dict(account=arguments['<account>'], date=correct_date.date()), ['account'])

    # Log the action
    log_action("Account: {0} modify_proposal_date: {1}".format(arguments['<account>'], correct_date.date()))

elif arguments['alloc_sus']:
    accounts = table.find()
    alloc_sus = 0
    for acc in accounts:
        if not acc['su_limit_hrs'] == -1:
            alloc_sus += acc['su_limit_hrs']
    print(alloc_sus)
