import csv
from datetime import date, datetime, time, timedelta
from io import StringIO
from logging import getLogger
from math import ceil
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import select

from bank import utils
from bank.exceptions import MissingProposalError
from bank.orm import Investor, InvestorArchive, Proposal, ProposalArchive, Session
from bank.settings import app_settings
from bank.utils import ProposalType, RequireRoot, ShellCmd

LOG = getLogger('bank.dao')


class Account:
    """Data access for user account information"""

    def __init__(self, account_name: str) -> None:
        """Data access for user account information

        args:
            account_name: The name of the user account
        """

        self.account_name = account_name

        # Make sure the account name has a corresponding proposal
        with Session() as session:
            if session.query(Proposal.account).filter_by(account=account_name).first() is None:
                raise MissingProposalError(f'Proposal for account `{account_name}` does not exist.')

    def _get_proposals(self) -> Tuple[Proposal, List[Investor]]:
        """Return any proposals associated with the account

        Returns:
            - The primary user proposal
            - A list of investments associated with the account
        """

        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name).first()
            investments = session.query(Investor).filter_by(account=self.account_name).all()

        return proposal, investments

    def proposal_info(self) -> None:
        """Print proposal information for the given account"""

        proposal, investments = self._get_proposals()
        print(proposal)
        for investor in investments:
            print(investor)

    def get_locked_state(self) -> bool:
        """Return whether the account is locked"""

        cmd = f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        return 'cpu=0' in ShellCmd(cmd).out

    @RequireRoot
    def set_locked_state(self, locked: bool, notify: bool = False) -> None:
        """Lock or unlock the user account

        Args:
            locked: The lock state to set
            notify: Send an email notifying the account holder of the new locked state
        """

        lock_state_int = 0 if locked else -1
        clusters = ','.join(app_settings.clusters)
        cmd = f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'

        ShellCmd(cmd).raise_err()
        if notify:
            self.proposal_expires_notification()

    def raw_cluster_usage(self, cluster: str) -> int:
        """Return the account usage on a given cluster in seconds"""

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        header, data = cmd.out.split('\n')[1:3]
        raw_usage_index = header.split('|').index("RawUsage")
        return int(data.split('|')[raw_usage_index])

    def get_raw_usage(self, *clusters: str, in_hours=False) -> Dict[str, int]:
        """Return the account usage on a given cluster in seconds

        Args:
            *clusters: The name of each cluster to check usage on
            in_hours: Return the usage in integer hours instead of seconds

        Returns:
            The account usage in seconds
        """

        if in_hours:
            return {c: time(second=self.raw_cluster_usage(c)).hour for c in clusters}

        return {c: self.raw_cluster_usage(c) for c in clusters}

    @RequireRoot
    def reset_raw_usage(self, *clusters: str) -> None:
        """Set raw account usage on the given clusters to zero"""

        clusters = ','.join(clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set RawUsage=0')

    def get_email_address(self) -> str:
        """Return the email address affiliated with the user account"""

        cmd = ShellCmd(f'sacctmgr show account {self.account_name} -P format=description -n')
        return f'{cmd.out}{app_settings.email_suffix}'

    def get_investment_status(self) -> str:
        """Return the current status of any account investments as an ascii table"""

        out = 'Total Investment SUs | Start Date | Current SUs | Withdrawn SUs | Rollover SUs\n'
        for row in Session().select(Investor).filter_by(account=self.account_name).all():
            out += (
                f"{row.service_units:20} | "
                f"{row.start_date.strftime(app_settings.date_format):>10} | "
                f"{row.current_sus:11} | "
                f"{row.withdrawn_sus:13} | "
                f"{row.rollover_sus:12}\n"
            )

        return out

    def notify_sus_limit(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()
        email_html = app_settings.notify_sus_limit_email_text.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=proposal.percent_notified,
            investment=self.get_investment_status()
        )

        utils.send_email(self, email_html)

    def three_month_proposal_expiry_notification(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()

        email_html = app_settings.three_month_proposal_expiry_notification_email.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=proposal.percent_notified,
            investment=self.get_investment_status()
        )

        utils.send_email(self, email_html)

    def proposal_expires_notification(self) -> None:
        statement = select(Proposal).filter_by(account=self.account_name)
        proposal = Session().execute(statement).scalars().first()

        email_html = app_settings.proposal_expires_notification_email.format(
            account=self.account_name,
            start=proposal.start_date.strftime(app_settings.date_format),
            expire=proposal.end_date.strftime(app_settings.date_format),
            usage=self.usage_string(),
            perc=proposal.percent_notified,
            investment=self.get_investment_status()
        )

        utils.send_email(self, email_html)

    def get_total_investor_sus(self, subtract_withdrawals: bool = False, include_rollovers: bool = False) -> int:
        """Return total service units on invested clusters

        Includes service units for any active proposals minus any
        overdrawn units.

        Args:
            subtract_withdrawals: Subtract any overdrawn units from the returned values
            include_rollovers: Include any rollover units from previous allocations

        Returns:
            A list of service units in each invested cluster
        """

        with Session() as session:
            investments = session.query(Investor).filter_by(account=self.account_name).all()

        total = 0
        for inv in investments:
            total += inv.service_units
            if subtract_withdrawals:
                total -= inv.withdrawn_sus

            if include_rollovers:
                total += inv.rollover_sus

        return total

    def get_usage_for_account(self) -> float:
        raw_usage = 0
        for cluster in app_settings.clusters:
            cmd = ShellCmd(f"sshare --noheader --account={self.account_name} --cluster={cluster} --format=RawUsage")
            raw_usage += int(cmd.out.split("\n")[1])

        return raw_usage / (60.0 * 60.0)

    def raise_missing_cluster_associations(self) -> None:
        """Raise exception if account associations do not exist for all clusters"""

        missing = []
        for cluster in app_settings.clusters:
            stmt = f"sacctmgr -n show assoc account={self.account_name} cluster={cluster} format=account,cluster"
            if ShellCmd(stmt).out == "":
                missing.append(cluster)

        if missing:
            raise ValueError(
                f"Associations missing for account `{self.account_name}` on clusters `{','.join(missing)}`")

    def usage_string(self) -> str:
        """Return the current account usage as an ascii table"""

        # Get total sus in all clusters
        proposal = Session().query(Proposal).filter_by(account=self.account_name).first()
        proposal_total = sum(getattr(proposal, c) for c in app_settings.clusters)
        investments_total = self.get_total_investor_sus(include_rollovers=True)

        aggregate_usage = 0
        with StringIO() as output:
            output.write(f"|{'-' * 82}|\n")
            output.write(f"|{'Proposal End Date':^30}|{proposal.end_date.strftime(app_settings.date_format):^51}|\n")
            for cluster in app_settings.clusters:
                output.write(f"|{'-' * 82}|\n")
                output.write(f"|{'Cluster: ' + cluster + ', Available SUs: ' + str(getattr(proposal, cluster)):^82}|\n")
                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
                output.write(f"|{'User':^20}|{'SUs Used':^30}|{'Percentage of Total':^30}|\n")
                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")

                total_usage = self.get_account_usage(cluster, getattr(proposal, cluster), output)
                aggregate_usage += total_usage

                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")
                if getattr(proposal, cluster) == 0:
                    output.write(f"|{'Overall':^20}|{total_usage:^30d}|{'N/A':^30}|\n")

                else:
                    output.write(
                        f"|{'Overall':^20}|{total_usage:^30d}|{100 * total_usage / getattr(proposal, cluster):^30.2f}|\n")

                output.write(f"|{'-' * 20}|{'-' * 30}|{'-' * 30}|\n")

            output.write(f"|{'Aggregate':^82}|\n")
            output.write(f"|{'-' * 40:^40}|{'-' * 41:^41}|\n")
            if investments_total > 0:
                investments_str = f"{investments_total:d}^a"
                output.write(f"|{'Investments Total':^40}|{investments_str:^41}|\n")
                output.write(
                    f"|{'Aggregate Usage (no investments)':^40}|{100 * aggregate_usage / proposal_total:^41.2f}|\n")
                output.write(
                    f"|{'Aggregate Usage':^40}|{100 * aggregate_usage / (proposal_total + investments_total):^41.2f}|\n")

            else:
                output.write(f"|{'Aggregate Usage':^40}|{100 * aggregate_usage / proposal_total:^41.2f}|\n")

            if investments_total > 0:
                output.write(f"|{'-' * 40:^40}|{'-' * 41:^41}|\n")
                output.write(f"|{'^a Investment SUs can be used across any cluster':^82}|\n")

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
                usage = time(second=data[raw_usage_idx]).hour
                if avail_sus == 0:
                    output.write(f"|{user:^20}|{usage:^30}|{'N/A':^30}|\n")

                else:
                    output.write(f"|{user:^20}|{usage:^30}|{100.0 * usage / avail_sus:^30.2f}|\n")
            else:
                total_cluster_usage = time(second=data[raw_usage_idx]).hour

        return total_cluster_usage

    def insert(self, prop_type: str, **sus_per_cluster: int) -> None:
        """Create a new proposal for the given account

        Args:
            prop_type: The type of proposal
            account: The account to add a proposal for
            **sus_per_cluster: Service units to add on to each cluster
        """

        # Account should have associations but not exist in the proposal table
        self.raise_missing_cluster_associations()
        utils.check_service_units_valid_clusters(sus_per_cluster)

        proposal_type = ProposalType.from_string(prop_type)
        proposal_duration = timedelta(days=365)
        start_date = date.today()
        new_proposal = Proposal(
            account=self.account_name,
            proposal_type=proposal_type.value,
            percent_notified=0,
            start_date=start_date,
            end_date=start_date + proposal_duration,
            **sus_per_cluster
        )

        with Session() as session:
            session.add(new_proposal)
            session.commit()

        su_string = ', '.join(f'{sus_per_cluster[k]} on {k}' for k in app_settings.clusters)
        LOG.info(
            f"Inserted proposal with type {proposal_type.name} for {self.account_name} with {su_string}")

    def investor(self, sus: int) -> None:
        """Add a new investor proposal for the given account

        Args:
            sus: The number of service units to add
        """

        # Account should have associations but not exist in the proposal table
        self.raise_missing_proposal()
        self.raise_missing_cluster_associations()

        # Investor accounts last 5 years
        proposal_type = utils.ProposalType.Investor
        start_date = date.today()
        end_date = start_date + timedelta(days=1825)

        # Service units should be a valid number
        utils.check_service_units_valid(sus)
        current_sus = ceil(sus / 5)

        new_investor = Investor(
            account=self.account_name,
            proposal_type=proposal_type.value,
            start_date=start_date,
            end_date=end_date,
            service_units=sus,
            current_sus=current_sus,
            withdrawn_sus=ceil(sus / 5),
            rollover_sus=0
        )

        with Session() as session:
            session.add(new_investor)
            session.commit()

        LOG.info(f"Inserted investment for {self.account_name} with per year allocations of `{current_sus}`")

    def modify(self, **sus_per_cluster: int) -> None:
        """Extend the proposal on an account 365 days and add the given number of service units"""

        # Account must exist in database
        self.raise_missing_proposal()
        utils.check_service_units_valid_clusters(sus_per_cluster)

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name).first()
            proposal.start_date = date.today()
            proposal.end_date = date.today() + timedelta(days=365)
            proposal.update(sus_per_cluster)
            session.commit()

        sus_as_string = ', '.join(f'{sus_per_cluster[k]} on {k}' for k in app_settings.clusters)
        LOG.info(f"Modified proposal for {self.account_name} with {sus_as_string}")

    def add(self, **sus_per_cluster: int) -> None:
        """Add service units for the given account / clusters

        Args:
            **sus_per_cluster: Service units to add on to each cluster
        """

        # Account must exist in database
        self.raise_missing_proposal()
        utils.check_service_units_valid_clusters(sus_per_cluster, greater_than_ten_thousand=False)

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name)
            for clus in app_settings.clusters:
                new_su = getattr(proposal, clus) + sus_per_cluster[clus]
                setattr(proposal, clus, new_su)

            session.commit()

        su_string = ', '.join(f'{getattr(proposal, k)} on {k}' for k in app_settings.clusters)
        LOG.info(f"Added SUs to proposal for {self.account_name}, new limits are {su_string}")

    def change(self, **sus_per_cluster: int) -> None:
        """Replace the currently allocated service units for an account with new values

        Args:
            **sus_per_cluster: New service unit allocation on to each cluster
        """

        self.raise_missing_proposal()
        utils.check_service_units_valid_clusters(sus_per_cluster)

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name)
            proposal.update(sus_per_cluster)
            session.commit()

        su_string = ', '.join(f'{sus_per_cluster[k]} on {k}' for k in app_settings.clusters)
        LOG.info(f"Changed proposal for {self.account_name} with {su_string}")

    def date(self, start_date: datetime) -> None:
        """Change the start date on an account's proposal

        Args:
            start_date: The new start date
        """

        self.raise_missing_proposal()

        date_str = start_date.strftime(app_settings.date_format)
        if start_date > datetime.today():
            raise ValueError(f'Start date cannot be in the future (received date: {date_str})')

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=self.account_name).first()
            proposal.start_date = start_date
            proposal.end_date = start_date + timedelta(days=365)
            session.commit()

        LOG.info(f'Modified proposal start date for {self.account_name} to {date_str}')

    def date_investment(self, start_date: datetime, inv_id: int) -> None:
        """Change the start date on an account's investment

        Args:
            start_date: The new start date
            inv_id: The investment id
        """

        self.raise_missing_proposal()

        # Date should be valid
        date_str = start_date.strftime(app_settings.date_format)
        if start_date > datetime.today():
            raise ValueError(f'Start date cannot be in the future (received date: {date_str})')

        # Update row in database
        with Session() as session:
            investment = session.query(Investor).filter_by(id=inv_id, account=self.account_name)
            if investment:
                investment.start_date = start_date
                investment.end_date = start_date + timedelta(days=1825)
                session.commit()

        LOG.info(
            f"Modify investment start date for investment #{inv_id} for account {self.account_name} to {start_date}")

    def check_sus_limit(self) -> None:
        # This is a complicated function, the steps:
        # 1. Get proposal for account and compute the total SUs from proposal
        # 2. Determine the current usage for the user across clusters
        # 3. Add any investment SUs to the total, archiving any exhausted investments
        # 4. Add archived investments associated to the current proposal

        session = Session()
        self.raise_missing_proposal()

        # Compute the Total SUs for the proposal period
        proposal_row = session.query(Proposal).filter_by(account=self.account_name).first()
        total_sus = sum([getattr(proposal_row, cluster) for cluster in app_settings.clusters])

        # Parse the used SUs for the proposal period
        used_sus_per_cluster = self.get_raw_usage(*app_settings.clusters, in_hours=True)
        used_sus = sum(used_sus_per_cluster.values())

        # Compute the sum of investment SUs, archiving any exhausted investments
        investor_rows = session.query(Investor).find(account=self.account_name).all()
        sum_investment_sus = 0
        for investor_row in investor_rows:
            # Check if investment is exhausted
            if investor_row.service_units - investor_row.withdrawn_sus == 0 and (
                used_sus
                >= (
                    total_sus
                    + sum_investment_sus
                    + investor_row.current_sus
                    + investor_row.rollover_sus
                )
                or investor_row.current_sus + investor_row.rollover_sus == 0
            ):
                to_insert = InvestorArchive(
                    service_units=investor_row.service_units,
                    current_sus=investor_row.current_sus,
                    rollover_sus=investor_row.rollover_sus,
                    start_date=investor_row.start_date,
                    end_date=investor_row.end_date,
                    exhaustion_date=date.today(),
                    account=self.account_name,
                    proposal_id=proposal_row.id,
                    investment_id=investor_row.id,
                )
                session.add(to_insert)
                investor_row.delete()
            else:
                sum_investment_sus += investor_row.current_sus + investor_row.rollover_sus

        total_sus += sum_investment_sus

        # Compute the sum of any archived investments associated with this proposal
        investor_archive_rows = session.query(InvestorArchive).filter_by(proposal_id=proposal_row.id)
        sum_investor_archive_sus = 0
        for investor_archive_row in investor_archive_rows:
            sum_investor_archive_sus += investor_archive_row.current_sus + investor_archive_row.rollover_sus

        total_sus += sum_investor_archive_sus

        notification_percent = proposal_row.percent_notified
        if notification_percent == 100:
            print(
                f"{datetime.now()}: Skipping account {self.account_name} because it should have already been notified and locked")
            return

        percent_usage = 100.0 * used_sus / total_sus

        # Update percent_notified in the table and notify account owner if necessary
        updated_notification_percent = utils.find_next_notification(percent_usage)
        if updated_notification_percent != notification_percent:
            proposal_row.percent_notified = updated_notification_percent.value
            self.notify_sus_limit()

            LOG.info(
                f"Updated proposal percent_notified to {updated_notification_percent} for {self.account_name}"
            )

        # Lock the account if necessary
        if updated_notification_percent == 100:
            if self.account_name != "root":
                self.set_locked_state(True)

                LOG.info(
                    f"The account for {self.account_name} was locked due to SUs limit"
                )

        session.commit()
        session.close()

    def check_proposal_end_date(self) -> None:
        """Alert and lock the user account if it is beyond it's proposal end date"""

        self.raise_missing_proposal()

        proposal_row = Session().query(Proposal).filter_by(account=self.account_name).first()
        today = date.today()
        three_months_before_end_date = proposal_row.end_date - timedelta(days=90)

        if today == three_months_before_end_date:
            self.three_month_proposal_expiry_notification()

        elif today == proposal_row.end_date:
            self.proposal_expires_notification()
            self.set_locked_state(True)
            LOG.info(
                f"The account for {self.account_name} was locked because it reached the end date {proposal_row.end_date}"
            )

    def withdraw(self, sus_to_withdraw: int) -> None:

        self.raise_missing_proposal()

        # Service units should be a valid number
        utils.check_service_units_valid(sus_to_withdraw)

        # First check if the user has enough SUs to withdraw
        available_investments = self.get_total_investor_sus(subtract_withdrawals=True)
        if sus_to_withdraw > available_investments:
            raise RuntimeError(
                f"Requested to withdraw {sus_to_withdraw} but the account only has {available_investments} SUs to withdraw")

        # Go through investments, oldest first and start withdrawing
        investments = Session().query(Investor).filter_by(account=self.account_name).all()
        for investment in investments:
            investment_remaining = investment.service_units - investment.withdrawn_sus

            # If not SUs to withdraw, skip the proposal entirely
            if investment_remaining == 0:
                print(f"No service units can be withdrawn from investment {investment.id}")
                continue

            # Determine what we can withdraw from current investment
            to_withdraw = min(sus_to_withdraw, investment_remaining)
            if sus_to_withdraw > investment_remaining:
                sus_to_withdraw -= investment_remaining

            else:
                sus_to_withdraw = 0

            # Update the current investment and log withdrawal
            with Session() as session:
                investment.current_sus += to_withdraw
                investment.withdrawn_sus += to_withdraw
                session.commit()

            LOG.info(
                f"Withdrew from investment {investment.id} for account {self.account_name} with value {to_withdraw}")

            # Determine if we are done processing investments
            if sus_to_withdraw == 0:
                return

    def usage(self) -> None:
        """Print the current service usage of the given account"""

        self.raise_missing_proposal()
        print(self.usage_string())

    def renewal(self, **sus) -> None:

        # Account associations better exist!
        self.raise_missing_proposal()
        self.raise_missing_cluster_associations()

        session = Session()

        # Make sure SUs are valid
        # Service units should be a valid number
        utils.check_service_units_valid_clusters(sus)

        # Archive current proposal, recording the usage on each cluster
        current_proposal = session.query(Proposal).filter_by(account=self.account_name).first()
        proposal_id = current_proposal.id

        current_usage = self.get_raw_usage(*app_settings.clusters, in_hours=True)
        to_insert = {f"{c}_usage": current_usage[c] for c in app_settings.clusters}
        for key in ["account", "start_date", "end_date"] + app_settings.clusters:
            to_insert[key] = getattr(current_proposal, key)
        session.add(ProposalArchive(**to_insert))

        # Archive any investments which are
        # - past their end_date
        # - withdraw + renewal leaves no current_sus and fully withdrawn account
        investor_rows = session.query(Investor).filter_by(account=self.account_name).all()
        for investor_row in investor_rows:
            archive = False
            if investor_row.end_date <= date.today():
                archive = True

            elif investor_row.current_sus == 0 and investor_row.withdrawn_sus == investor_row.service_units:
                archive = True

            if archive:
                to_insert = {
                    "service_units": investor_row.service_units,
                    "current_sus": investor_row.current_sus,
                    "start_date": investor_row.start_date,
                    "end_date": investor_row.end_date,
                    "exhaustion_date": date.today(),
                    "account": self.account_name,
                    "proposal_id": current_proposal.id,
                    "investor_id": investor_row.id,
                }
                session.add(InvestorArchive(**to_insert))
                investor_row.delete()

        # Renewal, should exclude any previously rolled over SUs
        current_investments = self.get_total_investor_sus()

        # If there are relevant investments,
        #     check if there is any rollover
        if current_investments != 0:
            need_to_rollover = 0
            # If current usage exceeds proposal, rollover some SUs, else rollover all SUs
            total_usage = sum([current_usage[c] for c in app_settings.clusters])
            total_proposal_sus = sum([getattr(current_proposal, c) for c in app_settings.clusters])
            if total_usage > total_proposal_sus:
                need_to_rollover = total_proposal_sus + current_investments - total_usage
            else:
                need_to_rollover = current_investments
            # Only half should rollover
            need_to_rollover /= 2

            # If the current usage exceeds proposal + investments or there is no investment, no need to rollover
            if need_to_rollover < 0 or current_investments == 0:
                need_to_rollover = 0

            if need_to_rollover > 0:
                # Go through investments and roll them over
                investor_rows = session.query(Investor).filter_by(account=self.account_name).all()
                for investor_row in investor_rows:
                    if need_to_rollover > 0:
                        years_left = investor_row.end_date.year - date.today().year
                        to_withdraw = (investor_row.service_units - investor_row.withdrawn_sus) // years_left
                        to_rollover = int(
                            investor_row.current_sus
                            if investor_row.current_sus < need_to_rollover
                            else need_to_rollover
                        )
                        investor_row.current_sus = to_withdraw
                        investor_row.rollover_sus = to_rollover
                        investor_row.withdrawn_sus += to_withdraw
                        need_to_rollover -= to_rollover

        # Insert new proposal
        proposal_duration = timedelta(days=365)
        start_date = date.today()
        end_date = start_date + proposal_duration

        prop = session.query(Proposal).filter_by(id=proposal_id).all()
        prop.percent_notified = 0
        prop.start_date = start_date
        prop.end_date = end_date
        for c in app_settings.clusters:
            setattr(prop, c, sus[c])

        # Set RawUsage to zero and unlock the account
        self.reset_raw_usage()
        self.set_locked_state(False)

        session.commit()
        session.close()


class Bank:

    @staticmethod
    def alloc_sus(path: Path) -> None:
        """Export allocated service units to a CSV file

        Args:
            path: The path to write exported data to
        """

        engine = create_engine(app_settings.db_path)
        columns = ('account', *app_settings.clusters)
        pd.read_sql_table(Proposal.__tablename__, engine, columns=columns).to_csv(path)

    @staticmethod
    def find_unlocked() -> None:
        """Print the names for all unexpired proposals with unlocked accounts"""

        with Session() as session:
            proposals = session.query(Proposal).filter_by(Proposal.end_date < date.today()).all()

        for proposal in proposals:
            account = Account(proposal.account)
            if not account.get_locked_state():
                print(account.account_name)

    @staticmethod
    def check_proposal_violations() -> None:
        """Iterate over all proposals and print any accounts with proposal violations"""

        with Session() as session:
            proposals = session.query(Proposal).all()

        for proposal in proposals:
            account = Account(proposal.account)
            investments = account.get_total_investor_sus(subtract_withdrawals=True)
            cluster_sus = account.get_raw_usage(*app_settings.clusters, in_hours=True)

            subtract_previous_investment = 0
            for cluster, used_sus in cluster_sus.items():
                avail_sus = getattr(proposal, cluster)
                if used_sus > (avail_sus + investments - subtract_previous_investment):
                    print(
                        f"Account {account.account_name}, Cluster {cluster}, Used SUs {used_sus}, Avail SUs {avail_sus}, Investment SUs {investments}")

                if used_sus > avail_sus:
                    subtract_previous_investment += investments - used_sus
