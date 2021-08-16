#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python

import csv
import json
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from enum import Enum
from io import StringIO
from math import floor
from shlex import split
from smtplib import SMTP
from subprocess import PIPE, Popen

import datafreeze
from bs4 import BeautifulSoup

from .constants import (
    CLUSTERS,
    date_format,
    email_suffix,
    investor_table,
    log_file_path,
    notify_sus_limit_email_text,
    proposal_expires_notification_email,
    proposal_table,
    three_month_proposal_expiry_notification_email
)
from .exceptions import CmdError


class ShellCmd:
    """Executes commands using the underlying command line environment"""

    def __init__(self, cmd: str) -> None:
        """Execute the given command in the underlying shell

        Args:
            cmd: The command to be run in a new pipe
        """

        if not cmd:
            raise ValueError('Command string cannot be empty')

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


class Right:
    def __init__(self, value):
        self.value = value


class Left:
    def __init__(self, reason):
        self.reason = reason


def unwrap_if_right(x):
    """Unwrap input if it belongs to the class ``Right`` by returning the attribute ``value``. Otherwise, exit."""

    if isinstance(x, Left):
        exit(x.reason)
    return x.value


def check_service_units_valid(units):
    """Return a proper natural number as a ``Right`` instance
    
    Args:
        units: Actual service units used as a parameter

    Returns:
        The passed value as an instance of ``Right``

    Raises:
        ValueError: If the input ``units`` is not a natural number
    """

    try:
        result = int(units)
    except ValueError:
        return Left(f"Given `{units}` which isn't a natural number")
    if result <= 0:
        return Left(f"Given `{units}` which isn't a natural number")
    return Right(result)


def check_service_units_valid_clusters(args, greater_than_ten_thousand=True):
    lefts = []
    result = {}
    for clus in CLUSTERS:
        try:
            if args[f"--{clus}"]:
                result[clus] = int(args[f"--{clus}"])
            else:
                result[clus] = 0
        except ValueError:
            lefts.append(
                f"Given non-integer value `{args[f'<{clus}>']}` for cluster `{clus}`"
            )
    if lefts:
        return Left("\n".join(lefts))
    total_sus = sum(result.values())
    if greater_than_ten_thousand and total_sus < 10000:
        return Left(f"Total SUs should exceed 10000 SUs, got `{total_sus}`")
    elif total_sus <= 0:
        return Left(f"Total SUs should be greater than zero, got `{total_sus}`")
    return Right(result)


def account_and_cluster_associations_exists(account):
    missing = []
    for cluster in CLUSTERS:
        cmd = ShellCmd(
            f"sacctmgr -n show assoc account={account} cluster={cluster} format=account,cluster"
        )
        if cmd.out == "":
            missing.append(cluster)

    if missing:
        return Left(
            f"Associations missing for account `{account}` on clusters `{','.join(missing)}`"
        )
    return Right(account)


def account_exists_in_table(table, account):
    q = table.find_one(account=account)
    if not q is None:
        return Right(q)
    else:
        return Left(f"Account `{account}` doesn't exist in the database")


def log_action(s):
    with log_file_path.open("a+") as f:
        f.write(f"{datetime.now()}: {s}\n")


def get_usage_for_account(account):
    raw_usage = 0
    for cluster in CLUSTERS:
        cmd = ShellCmd(
            f"sshare --noheader --account={account} --cluster={cluster} --format=RawUsage"
        )
        raw_usage += int(cmd.out.split("\n")[1])
    return raw_usage / (60.0 * 60.0)


def find_next_notification(usage):
    members = list(PercentNotified)

    exceeded = [usage > x.to_percentage() for x in members]

    try:
        index = exceeded.index(False)
        result = PercentNotified.Zero if index == 0 else members[index - 1]
    except ValueError:
        result = PercentNotified.Hundred

    return result


class PercentNotified(Enum):
    Zero = 0
    TwentyFive = 1
    Fifty = 2
    SeventyFive = 3
    Ninety = 4
    Hundred = 5

    def succ(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) + 1
        if index >= len(members):
            return members[0]
        else:
            return members[index]

    def pred(self):
        cls = self.__class__
        members = list(cls)
        index = members.index(self) - 1
        if index < 0:
            return members[5]
        else:
            return members[index]

    def to_percentage(self):
        if self == PercentNotified.Zero:
            return 0.0
        elif self == PercentNotified.TwentyFive:
            return 25.0
        elif self == PercentNotified.Fifty:
            return 50.0
        elif self == PercentNotified.SeventyFive:
            return 75.0
        elif self == PercentNotified.Ninety:
            return 90.0
        else:
            return 100.0


class ProposalType(Enum):
    Proposal = 0
    Class = 1
    Investor = 2


def parse_proposal_type(s):
    if s == "proposal":
        return Right(ProposalType.Proposal)
    elif s == "class":
        return Right(ProposalType.Class)
    else:
        return Left(f"Valid proposal types are `proposal` or `class`, not `{s}`")


def get_proposal_duration(t):
    return timedelta(days=365) if t == ProposalType.Proposal else timedelta(days=122)


def check_date_valid(d):
    try:
        date = datetime.strptime(d, "%m/%d/%y")
    except:
        return Left(f"Could not parse date (e.g. 12/01/19), got `{date}`")

    if date > date.today():
        return Left(f"Parsed `{date}`, but start dates shouldn't be in the future")

    return Right(date)


def get_raw_usage_in_hours(account, cluster):
    cmd = ShellCmd(f"sshare -A {account} -M {cluster} -P -a")

    # Only the second and third line are necessary, wrapped in text buffer
    sio = StringIO("\n".join(cmd.out.split("\n")[1:3]))

    # use built-in CSV reader to read header and data
    reader = csv.reader(sio, delimiter="|")
    header = next(reader)
    data = next(reader)

    # Find the index of RawUsage from the header
    raw_usage_idx = header.index("RawUsage")
    return convert_to_hours(data[raw_usage_idx])


def lock_account(account):
    clusters = ",".join(CLUSTERS)
    ShellCmd(
        f"sacctmgr -i modify account where account={account} cluster={clusters} set GrpTresRunMins=cpu=0"
    )


def unlock_account(account):
    clusters = ",".join(CLUSTERS)
    ShellCmd(
        f"sacctmgr -i modify account where account={account} cluster={clusters} set GrpTresRunMins=cpu=-1"
    )


def reset_raw_usage(account):
    clusters = ",".join(CLUSTERS)
    ShellCmd(
        f"sacctmgr -i modify account where account={account} cluster={clusters} set RawUsage=0"
    )


def get_investment_status(account):
    total_investment_h = "Total Investment SUs"
    start_date_h = "Start Date"
    current_sus_h = "Current SUs"
    withdrawn_h = "Withdrawn SUs"
    rollover_h = "Rollover SUs"

    total_investment_w = 20
    start_date_w = 10
    current_sus_w = 11
    withdrawn_w = 13
    rollover_w = 12

    result_s = f"{total_investment_h} | {start_date_h} | {current_sus_h} | {withdrawn_h} | {rollover_h}\n"

    for row in investor_table.find(account=account):
        per_year = f"per_year"
        current = f"current_sus"
        withdrawn = f"withdrawn_sus"
        rollover = f"rollover_sus"
        result_s += f"{row['service_units']:20} | {row['start_date'].strftime(date_format):>10} | {row[current]:11} | {row[withdrawn]:13} | {row[rollover]:12}\n"

    return result_s


def notify_sus_limit(account):
    proposal_row = proposal_table.find_one(account=account)
    email_html = notify_sus_limit_email_text.format(
        account=account,
        start=proposal_row["start_date"].strftime(date_format),
        expire=proposal_row["end_date"].strftime(date_format),
        usage=usage_string(account),
        perc=PercentNotified(proposal_row["percent_notified"]).to_percentage(),
        investment=get_investment_status(account)
    )

    send_email(email_html, account)


def get_account_email(account):
    cmd = ShellCmd(f"sacctmgr show account {account} -P format=description -n")
    return f"{cmd.out}{email_suffix}"


def send_email(email_html, account):
    # Extract the text from the email
    soup = BeautifulSoup(email_html, "html.parser")
    email_text = soup.get_text()

    msg = EmailMessage()
    msg.set_content(email_text)
    msg.add_alternative(email_html, subtype="html")
    msg["Subject"] = f"Your allocation on H2P for account: {account}"
    msg["From"] = "noreply@pitt.edu"
    msg["To"] = get_account_email(account)

    with SMTP("localhost") as s:
        s.send_message(msg)


def three_month_proposal_expiry_notification(account):
    proposal_row = proposal_table.find_one(account=account)

    email_html = three_month_proposal_expiry_notification_email.format(
        account=account,
        start=proposal_row["start_date"].strftime(date_format),
        expire=proposal_row["end_date"].strftime(date_format),
        usage=usage_string(account),
        perc=PercentNotified(proposal_row["percent_notified"]).to_percentage(),
        investment=get_investment_status(account)
    )

    send_email(email_html, account)


def proposal_expires_notification(account):
    proposal_row = proposal_table.find_one(account=account)

    email_html = proposal_expires_notification_email.format(
        account=account,
        start=proposal_row["start_date"].strftime(date_format),
        expire=proposal_row["end_date"].strftime(date_format),
        usage=usage_string(account),
        perc=PercentNotified(proposal_row["percent_notified"]).to_percentage(),
        investment=get_investment_status(account)
    )

    send_email(email_html, account)


def get_available_investor_sus(account):
    res = []
    ods = investor_table.find(account=account)
    for od in ods:
        res.append(od["service_units"] - od[f"withdrawn_sus"])
    return res


def get_current_investor_sus(account):
    res = []
    ods = investor_table.find(account=account)
    for od in ods:
        res.append(od[f"current_sus"] + od[f"rollover_sus"])
    return res


def get_current_investor_sus_no_rollover(account):
    res = []
    ods = investor_table.find(account=account)
    for od in ods:
        res.append(od[f"current_sus"])
    return res


def convert_to_hours(usage):
    return floor(int(usage) / (60.0 * 60.0))


def get_account_usage(account, cluster, avail_sus, output):
    cmd = ShellCmd(f"sshare -A {account} -M {cluster} -P -a")
    # Second line onward, required
    sio = StringIO("\n".join(cmd.out.split("\n")[1:]))

    # use built-in CSV reader to read header and data
    reader = csv.reader(sio, delimiter="|")
    header = next(reader)
    raw_usage_idx = header.index("RawUsage")
    user_idx = header.index("User")
    for idx, data in enumerate(reader):
        if idx != 0:
            user = data[user_idx]
            usage = convert_to_hours(data[raw_usage_idx])
            if avail_sus == 0:
                output.write(f"|{user:^20}|{usage:^30}|{'N/A':^30}|\n")
            else:
                output.write(
                    f"|{user:^20}|{usage:^30}|{100.0 * usage / avail_sus:^30.2f}|\n"
                )
        else:
            total_cluster_usage = convert_to_hours(data[raw_usage_idx])

    return total_cluster_usage


def freeze_if_not_empty(items, path):
    force_eval = list(items)
    if force_eval:
        datafreeze.freeze(force_eval, format="json", filename=path)
    else:
        with open(path, "w") as f:
            f.write("{}\n")


def usage_string(account):
    proposal = proposal_table.find_one(account=account)
    investments = sum(get_current_investor_sus(account))
    proposal_total = sum([proposal[c] for c in CLUSTERS])
    aggregate_usage = 0
    with StringIO() as output:
        output.write(f"|{'-' * 82}|\n")
        output.write(
            f"|{'Proposal End Date':^30}|{proposal['end_date'].strftime(date_format):^51}|\n"
        )
        for cluster in CLUSTERS:
            output.write(f"|{'-' * 82}|\n")
            output.write(
                f"|{'Cluster: ' + cluster + ', Available SUs: ' + str(proposal[cluster]):^82}|\n"
            )
            output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
            output.write(
                f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|\n"
            )
            output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
            total_usage = get_account_usage(account, cluster, proposal[cluster], output)
            aggregate_usage += total_usage
            output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
            if proposal[cluster] == 0:
                output.write(f"|{'Overall':^20}|{total_usage:^30d}|{'N/A':^30}|\n")
            else:
                output.write(
                    f"|{'Overall':^20}|{total_usage:^30d}|{100 * total_usage / proposal[cluster]:^30.2f}|\n"
                )
            output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
        output.write(f"|{'Aggregate':^82}|\n")
        output.write(f"|{'-' * 40:^40}|{'-' * 41:^41}|\n")
        if investments > 0:
            investments_total = f"{investments:d}^a"
            output.write(f"|{'Investments Total':^40}|{investments_total:^41}|\n")
            output.write(
                f"|{'Aggregate Usage (no investments)':^40}|{100 * aggregate_usage / proposal_total:^41.2f}|\n"
            )
            output.write(
                f"|{'Aggregate Usage':^40}|{100 * aggregate_usage / (proposal_total + investments):^41.2f}|\n"
            )
        else:
            output.write(
                f"|{'Aggregate Usage':^40}|{100 * aggregate_usage / proposal_total:^41.2f}|\n"
            )
        if investments > 0:
            output.write(f"|{'-' * 40:^40}|{'-' * 41:^41}|\n")
            output.write(
                f"|{'^a Investment SUs can be used across any cluster':^82}|\n"
            )
        output.write(f"|{'-' * 82}|\n")
        return output.getvalue().strip()


def years_left(end):
    return end.year - date.today().year


def ask_destructive(args):
    if args["--yes"]:
        choice = "yes"
    else:
        print(
            "DANGER: This function OVERWRITES crc_bank.db, are you sure you want to do this? [y/N]"
        )
        choice = input().lower()
    return choice


def import_from_json(args, table, table_type):
    choice = ask_destructive(args)
    if choice == "yes" or choice == "y":
        if table_type == ProposalType.Proposal:
            filename = "<proposal.json>"
        elif table_type == ProposalType.Investor:
            filename = "<investor.json>"
        else:
            raise ValueError
        with open(args[filename], "r") as fp:
            contents = json.load(fp)
            table.drop()
            if "results" in contents.keys():
                for item in contents["results"]:
                    start_date_split = [int(x) for x in item["start_date"].split("-")]
                    item["start_date"] = date(
                        start_date_split[0], start_date_split[1], start_date_split[2]
                    )
                    end_date_split = [int(x) for x in item["end_date"].split("-")]
                    item["end_date"] = date(
                        end_date_split[0], end_date_split[1], end_date_split[2]
                    )
                    del item["id"]

                table.insert_many(contents["results"])


def is_account_locked(account):
    cmd = ShellCmd(
        f"sacctmgr -n -P show assoc account={account} format=grptresrunmins"
    )

    if "cpu=0" in cmd.out:
        return True
    return False
