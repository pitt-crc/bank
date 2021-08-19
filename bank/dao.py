import csv
from io import StringIO
from typing import List, Union

from sqlalchemy import select

from bank.utils import Left, PercentNotified, Right, ShellCmd, convert_to_hours
from .orm import Investor, Proposal, Session
from .settings import app_settings


class Account:
    """Data access for user account information"""

    def __init__(self, account_name: str) -> None:
        self.account_name = account_name

    def is_account_locked(self) -> bool:
        """Return whether the account is locked"""

        cmd = ShellCmd(f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins')
        return 'cpu=0' in cmd.out

    def usage_string(self) -> str:
        """Return the current account usage as an ascii table"""

        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()

        investments = sum(self.get_current_investor_sus())
        proposal_total = sum([getattr(proposal, c) for c in app_settings.clusters])
        aggregate_usage = 0
        with StringIO() as output:
            output.write(f"|{'-' * 82}|\n")
            output.write(
                f"|{'Proposal End Date':^30}|{proposal.end_date.strftime(app_settings.date_format):^51}|\n"
            )
            for cluster in app_settings.clusters:
                output.write(f"|{'-' * 82}|\n")
                output.write(
                    f"|{'Cluster: ' + cluster + ', Available SUs: ' + str(getattr(proposal, cluster)):^82}|\n"
                )
                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
                output.write(
                    f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|\n"
                )
                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
                total_usage = self.get_account_usage(cluster, getattr(proposal, cluster), output)
                aggregate_usage += total_usage
                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
                if getattr(proposal, cluster) == 0:
                    output.write(f"|{'Overall':^20}|{total_usage:^30d}|{'N/A':^30}|\n")
                else:
                    output.write(
                        f"|{'Overall':^20}|{total_usage:^30d}|{100 * total_usage / getattr(proposal, cluster):^30.2f}|\n"
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

    def get_account_usage(self, cluster, avail_sus, output):
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
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

    def get_raw_usage_in_hours(self, cluster: str) -> float:
        """Return the account's usage on a given cluster in hours

        Args:
            cluster: The name of the cluster to check usage on

        Returns:
            The account usage in hours
        """

        # Only the second and third line are necessary, wrapped in text buffer
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        sio = StringIO("\n".join(cmd.out.split("\n")[1:3]))

        # use built-in CSV reader to read header and data
        reader = csv.reader(sio, delimiter="|")
        header = next(reader)
        data = next(reader)

        # Find the index of RawUsage from the header
        raw_usage_idx = header.index("RawUsage")
        return convert_to_hours(data[raw_usage_idx])

    def lock_account(self) -> None:
        """Lock the user account"""

        clusters = ','.join(app_settings.clusters)
        ShellCmd(
            f"sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu=0")

    def unlock_account(self) -> None:
        """Unlock the user account"""

        clusters = ','.join(app_settings.clusters)
        ShellCmd(
            f"sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu=-1")

    def reset_raw_usage(self) -> None:
        """Set reset raw usage on all clusters to zero"""

        clusters = ','.join(app_settings.clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set RawUsage=0')

    def get_investment_status(self) -> str:
        total_investment_h = "Total Investment SUs"
        start_date_h = "Start Date"
        current_sus_h = "Current SUs"
        withdrawn_h = "Withdrawn SUs"
        rollover_h = "Rollover SUs"

        result_s = f"{total_investment_h} | {start_date_h} | {current_sus_h} | {withdrawn_h} | {rollover_h}\n"

        statement = select(Proposal).filter_by(account=self.account_name)
        for row in Session().execute(statement).scalars().all():
            result_s += f"{row.service_units:20} | {row.start_date.strftime(app_settings.date_format):>10} | {row.current_sus:11} | {row.withdrawn_sus:13} | {row.rollover_sus:12}\n"

        return result_s

    def notify_sus_limit(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()
        email_html = app_settings.notify_sus_limit_email_text.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
            investment=self.get_investment_status()
        )

        self.send_email(email_html)

    def get_account_email(self) -> str:
        cmd = ShellCmd(f'sacctmgr show account {self.account_name} -P format=description -n')
        return f'{cmd.out}{app_settings.email_suffix}'

    def three_month_proposal_expiry_notification(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()

        email_html = app_settings.three_month_proposal_expiry_notification_email.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
            investment=self.get_investment_status()
        )

        self.send_email(email_html)

    def proposal_expires_notification(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()

        email_html = app_settings.proposal_expires_notification_email.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
            investment=self.get_investment_status()
        )

        self.send_email(email_html)

    def get_available_investor_sus(self) -> List[float]:
        """Return available service units on invested clusters

        Includes service units for any active proposals minus any
        overdrawn units.

        Returns:
            A list of service units in each invested cluster
        """

        res = []
        statement = select(Investor).filter_by(account=self.account_name)
        for od in Session().execute(statement).scalars().all():
            res.append(od.service_units - od.withdrawn_sus)

        return res

    def get_current_investor_sus(self) -> List[float]:
        """Return all account service units available on invested clusters

        Includes service units for any active proposals in addition
        to any rollover units from previous accounts

        Returns:
            A list of service units in each invested cluster
        """

        res = []
        statement = select(Investor).filter_by(account=self.account_name)
        for od in Session().execute(statement).scalars().all():
            res.append(od.current_sus + od.rollover_sus)

        return res

    def get_current_investor_sus_no_rollover(self) -> List[float]:
        """Return current service units available on invested clusters

        Includes service units for any active proposals in addition
        to any rollover units from previous accounts

        Returns:
            A list of service units in each invested cluster
        """

        res = []
        statement = select(Investor).filter_by(account=self.account_name)
        for od in Session().execute(statement).scalars().all():
            res.append(od.current_sus)

        return res

    def get_usage_for_account(self) -> float:
        raw_usage = 0
        for cluster in app_settings.clusters:
            cmd = ShellCmd(
                f"sshare --noheader --account={self.account_name} --cluster={cluster} --format=RawUsage"
            )
            raw_usage += int(cmd.out.split("\n")[1])
        return raw_usage / (60.0 * 60.0)

    def account_and_cluster_associations_exists(self) -> Union[Left, Right]:
        missing = []
        for cluster in app_settings.clusters:
            cmd = ShellCmd(
                f"sacctmgr -n show assoc account={self.account_name} cluster={cluster} format=account,cluster"
            )
            if cmd.out == "":
                missing.append(cluster)

        if missing:
            return Left(
                f"Associations missing for account `{self.account_name}` on clusters `{','.join(missing)}`"
            )
        return Right(self.account_name)
