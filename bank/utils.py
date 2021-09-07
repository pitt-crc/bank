#!/usr/bin/env /ihome/crc/install/python/miniconda3-3.7/bin/python

from __future__ import annotations

from datetime import date, datetime
from email.message import EmailMessage
from enum import Enum
from functools import wraps
from math import floor
from os import geteuid
from pathlib import Path
from shlex import split
from smtplib import SMTP
from subprocess import PIPE, Popen
from typing import Any, List

import datafreeze
from bs4 import BeautifulSoup

from .exceptions import CmdError
from .settings import app_settings


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


class RequireRoot:
    """Function decorator for requiring root privileges"""

    @staticmethod
    def require_root_access() -> None:
        """Raise an error if the current session does not have root permissions

        Raises:
            RuntimeError: If session is not root
        """

        if geteuid() != 0:
            raise RuntimeError("This action must be run with sudo privileges")

    def __new__(self, func: callable) -> callable:
        @wraps(func)
        def wrapped(*args, **kwargs) -> Any:
            self.require_root_access()
            return func(*args, **kwargs)

        return wrapped


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


def check_service_units_valid_clusters(sus, greater_than_ten_thousand=True):
    for clus, val in sus.items():
        try:
            sus[clus] = int(val)

        except ValueError:
            raise ValueError(f"Given non-integer value `{val}` for cluster `{clus}`")

    total_sus = sum(sus.values())
    if greater_than_ten_thousand and total_sus < 10000:
        raise ValueError(f"Total SUs should exceed 10000 SUs, got `{total_sus}`")

    elif total_sus <= 0:
        raise ValueError(f"Total SUs should be greater than zero, got `{total_sus}`")


def log_action(s):
    with app_settings.log_path.open('a+') as f:
        f.write(f"{datetime.now()}: {s}\n")


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

    @classmethod
    def from_string(cls, name: str) -> ProposalType:
        try:
            return cls(getattr(cls, name.title()))

        except AttributeError:
            raise ValueError(f'Invalid proposal type: `{name}`')


def check_date_valid(d):
    """Checks if date is valid

    Args:
        d: date

    Returns:
        a valid date
    """
    try:
        date = datetime.strptime(d, "%m/%d/%y")
    except:
        return Left(f"Could not parse date (e.g. 12/01/19), got `{date}`")

    if date > date.today():
        return Left(f"Parsed `{date}`, but start dates shouldn't be in the future")

    return Right(date)


def convert_to_hours(usage):
    """Converts hours to seconds

    Args:

    usage: variable for hours
    """
    seconds_in_hour = 60 * 60
    return floor(int(usage) / (seconds_in_hour))


def freeze_if_not_empty(items: List, path: Path):
    """Checks if list filename is empty or not

    Args:
        items: a list
        path: filename parg
    """
    force_eval = [dict(p) for p in items]
    if force_eval:
        datafreeze.freeze(force_eval, format="json", filename=path)
    else:
        with open(path, "w") as f:
            f.write("{}\n")


def years_left(end):
    """Determines how many years left

    Args:
        end: the last year left

    Returns:
        years left in proposal
    """
    return end.year - date.today().year


def ask_destructive(force=False):
    """Checks if function is destructive

    Args: 
        force: defaults to False

    Returns:
        a choice that shows if function is destructive or not 
    """
    if force:
        choice = "yes"
    else:
        print(
            "DANGER: This function OVERWRITES crc_bank.db, are you sure you want to do this? [y/N]"
        )
        choice = input().lower()
    return choice


# def import_from_json(filepath: str, table, overwrite: bool):
#     filepath = Path(filepath)
#
#     choice = ask_destructive(force=overwrite)
#     if choice not in ("yes", "y"):
#         return
#
#     with filepath.open("r") as fp, Session() as session:
#         contents = json.load(fp)
#         session.query(table).delete()  # Delete existing rows in table
#         if "results" in contents.keys():
#             for item in contents["results"]:
#                 start_date_split = [int(x) for x in item["start_date"].split("-")]
#                 item["start_date"] = date(
#                     start_date_split[0], start_date_split[1], start_date_split[2]
#                 )
#
#                 end_date_split = [int(x) for x in item["end_date"].split("-")]
#                 item["end_date"] = date(
#                     end_date_split[0], end_date_split[1], end_date_split[2]
#                 )
#
#                 del item["id"]
#                 session.add(table(**item))
#
#         session.commit()

class EmailTemplate:
    def __init__(self, msg:str):
        """Args:
            msg: message in email
        """
        self.msg= msg
       
    def format(self, account, proposal)->EmailTemplate:
        """Formats email

        Args:
            account: the account to send an email to 
            proposal: the email proposal for account

        Returns:
            copy of format email message
        """
        format_message=self.msg.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
            investment=self.get_investment_status())

        return EmailTemplate(format_message)
        #return self.__class__(format_message)
        
    #'''
    #def send_email(self, account, email_html: str) -> None:
   # """Send an email to a user account

    #Args:
    #    account: The account to send an email to
    #    email_html: The content of the email
    #"""

    # Extract the text from the email
    
   # soup = BeautifulSoup(email_html, "html.parser")
    #email_text = soup.get_text()

    #msg = EmailMessage()
    #msg.set_content(email_text)
    #msg.add_alternative(email_html, subtype="html")
    #msg["Subject"] = f"Your allocation on H2P for account: {account.account_name}"
    #msg["From"] = "noreply@pitt.edu"
    #msg["To"] = account.get_email_address()

    #with SMTP("localhost") as s:
     #   s.send_message(msg)
#'''