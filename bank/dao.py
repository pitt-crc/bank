import csv
import json
from datetime import date, datetime, timedelta
from io import StringIO
from math import ceil
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select

from bank import utils
from bank.orm import Investor, InvestorArchive, Proposal, ProposalArchive, Session
from bank.settings import app_settings
from bank.utils import PercentNotified, ProposalType, RequireRoot, ShellCmd, convert_to_hours


class Account:
    """Data access for user account information"""

    def __init__(self, account_name: str) -> None:
        """Data access for user account information

        args:
            account_name: The name of the user account
        """

        self.account_name = account_name

    def check_has_proposal(self, raise_if: bool = False) -> bool:
        """Return if the account has an associated proposal in the database

        Args:
            raise_if: Raise an error if the return matches this value

        Returns:
            Whether a database entry exists as a boolean

        Raises:
            A ``ValueError`` if the return value matches ``raise_if``
        """

        has_proposal = Proposal.check_matching_entry_exists(account=self.account_name)
        if has_proposal is raise_if:
            condition = 'already exists' if has_proposal else 'does not exist'
            raise RuntimeError(f'Proposal for account `{self.account_name}` {condition}.')

        return has_proposal

    def get_locked_state(self) -> bool:
        """Return whether the account is locked"""

        return 'cpu=0' in ShellCmd(
            f'sacctmgr -n -P show assoc account={self.account_name} format=grptresrunmins'
        ).out

    def set_locked_state(self, locked: bool) -> None:
        """Lock or unlock the user account

        Args:
            locked: The lock state to set
        """

        lock_state_int = 0 if locked else -1
        clusters = ','.join(app_settings.clusters)
        ShellCmd(
            f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set GrpTresRunMins=cpu={lock_state_int}'
        )

    def _raw_cluster_usage(self, cluster: str) -> None:
        """Return the account usage on a given cluster in seconds"""

        # Only the second and third line are necessary from the output table
        cmd = ShellCmd(f"sshare -A {self.account_name} -M {cluster} -P -a")
        header, data = cmd.out.split('\n')[1:3]
        raw_usage_index = header.split('|').index("RawUsage")
        return data.split('|')[raw_usage_index]

    def get_raw_usage(self, *clusters: str, in_hours=False) -> Dict[str, int]:
        """Return the account usage on a given cluster in seconds

        Args:
            *clusters: The name of each cluster to check usage on
            in_hours: Return the usage in integer hours instead of seconds

        Returns:
            The account usage in seconds
        """

        if in_hours:
            return {c: convert_to_hours(self._raw_cluster_usage(c)) for c in clusters}

        return {c: self._raw_cluster_usage(c) for c in clusters}

    def reset_raw_usage(self, *clusters) -> None:
        """Set raw account usage on the given clusters to zero"""

        clusters = ','.join(clusters)
        ShellCmd(f'sacctmgr -i modify account where account={self.account_name} cluster={clusters} set RawUsage=0')

    def get_email_address(self) -> str:
        """Return the email address affiliated with the user account"""

        cmd = ShellCmd(f'sacctmgr show account {self.account_name} -P format=description -n')
        return f'{cmd.out}{app_settings.email_suffix}'

    def get_investment_status(self) -> str:
        """Return the current status of any account investments as an ascii table"""

        out = f"Total Investment SUs | Start Date | Current SUs | Withdrawn SUs | Rollover SUs\n"
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
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
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
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
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
            perc=PercentNotified(proposal.percent_notified).to_percentage(),
            investment=self.get_investment_status()
        )

        utils.send_email(self, email_html)

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
        investments_total = sum(self.get_current_investor_sus())

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
                usage = convert_to_hours(data[raw_usage_idx])
                if avail_sus == 0:
                    output.write(f"|{user:^20}|{usage:^30}|{'N/A':^30}|\n")

                else:
                    output.write(f"|{user:^20}|{usage:^30}|{100.0 * usage / avail_sus:^30.2f}|\n")
            else:
                total_cluster_usage = convert_to_hours(data[raw_usage_idx])

        return total_cluster_usage


class Bank:

    @staticmethod
    def insert(prop_type: str, account_name: str, **sus_per_cluster: int) -> None:
        """Create a new proposal for the given account

        Args:
            prop_type: The type of proposal
            account_name: The name of the account to add a proposal for
            **sus_per_cluster: Service units to add on to each cluster
        """

        # Account should have associations but not exist in the proposal table
        account = Account(account_name)
        account.check_has_proposal(raise_if=True)
        account.raise_missing_cluster_associations()

        proposal_type = ProposalType.from_string(prop_type)
        utils.check_service_units_valid_clusters(sus_per_cluster)
        proposal_duration = timedelta(days=365)
        start_date = date.today()

        new_proposal = Proposal(
            account=account.account_name,
            proposal_type=proposal_type.value,
            percent_notified=PercentNotified.Zero.value,
            start_date=start_date,
            end_date=start_date + proposal_duration,
            **sus_per_cluster
        )

        with Session() as session:
            session.add(new_proposal)
            session.commit()

        utils.log_action(
            f"Inserted proposal with type {proposal_type.name} for {account.account_name} with "
            f"`{sus_per_cluster['smp']}` on SMP, "
            f"`{sus_per_cluster['mpi']}` on MPI, "
            f"`{sus_per_cluster['gpu']}` on GPU, and "
            f"`{sus_per_cluster['htc']}` on HTC"
        )

    @staticmethod
    def investor(account_name: str, sus: int) -> None:
        """Add a new investor proposal for the given account

        Args:
            account_name: The name of the account
            sus: The number of service units to add
        """

        # Account should have associations but not exist in the proposal table
        account = Account(account_name)
        account.check_has_proposal(raise_if=False)
        account.raise_missing_cluster_associations()

        # Investor accounts last 5 years
        proposal_type = utils.ProposalType.Investor
        start_date = date.today()
        end_date = start_date + timedelta(days=1825)

        # Service units should be a valid number
        sus = utils.unwrap_if_right(utils.check_service_units_valid(sus))

        current_sus = ceil(sus / 5)
        new_investor = Investor(
            account=account_name,
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

        utils.log_action(
            f"Inserted investment for {account_name} with per year allocations of `{current_sus}`"
        )

    @staticmethod
    def info(account_name: str) -> None:
        """Print proposal information for the given account

        Args:
            account_name: The name of the account
        """

        account = Account(account_name)
        account.check_has_proposal(raise_if=False)
        proposal = Session().query(Proposal).filter_by(account=account_name).first()

        print("Proposal")
        print("--------")
        print(json.dumps(proposal.to_json(), indent=2))
        print()

        investors = Session().query(Investor).filter_by(account=account_name).all()
        for investor in investors:
            print(f"Investment: {investor.id:3}")
            print(f"---------------")
            print(json.dumps(investor.to_json(), indent=2))
            print()

    @staticmethod
    def modify(account_name, **sus_per_cluster: int) -> None:
        """Extend the proposal on an account 365 days and add the given number of service units"""

        # Account must exist in database
        Account(account_name).check_has_proposal(raise_if=False)
        utils.check_service_units_valid_clusters(sus_per_cluster)

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=account_name).first()
            proposal.start_date = date.today()
            proposal.end_date = date.today() + timedelta(days=365)
            for clus in app_settings.clusters:
                setattr(proposal, clus,  sus_per_cluster[clus])
            session.commit()

        utils.log_action(
            f"Modified proposal for {account_name} with "
            f"`{sus_per_cluster['smp']}` on SMP, "
            f"`{sus_per_cluster['mpi']}` on MPI, "
            f"`{sus_per_cluster['gpu']}` on GPU, and "
            f"`{sus_per_cluster['htc']}` on HTC"
        )

    def add(self, account_name, **sus_per_cluster) -> None:

        # Account must exist in database
        Account(account_name).check_has_proposal(raise_if=False)
        utils.check_service_units_valid_clusters(sus_per_cluster, greater_than_ten_thousand=False)

        # Update row in database
        with Session() as session:
            proposal = session.query(Proposal).filter_by(account=account_name)
            for clus in app_settings.clusters:
                new_su = getattr(proposal, clus) + sus_per_cluster[clus]
                setattr(proposal, clus, new_su)

            session.commit()

        utils.log_action(
            f"Added SUs to proposal for {account_name}, new limits are `{proposal['smp']}` on SMP, `{proposal['mpi']}` on MPI, `{proposal['gpu']}` on GPU, and `{proposal['htc']}` on HTC"
        )

    def change(self, account_name, smp, mpi, gpu, htc) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        sus = {'smp': smp, 'htc': htc, 'mpi': mpi, 'gpu': gpu}
        utils.check_service_units_valid_clusters(sus)

        # Update row in database
        with Session() as session:
            od = session.query(Proposal).filter_by(account=account_name)
            for clus in app_settings.clusters:
                setattr(od, clus, sus[clus])

            session.commit()

        utils.log_action(
            f"Changed proposal for {account_name} with `{sus['smp']}` on SMP, `{sus['mpi']}` on MPI, `{sus['gpu']}` on GPU, and `{sus['htc']}` on HTC"
        )

    def date(self, account_name, date) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Date should be valid
        start_date = utils.unwrap_if_right(utils.check_date_valid(date))

        # Update row in database
        with Session() as session:
            od = session.query(Proposal).filter_by(account=account_name).first()
            proposal_duration = utils.get_proposal_duration(
                utils.ProposalType(od.proposal_type)
            )

            od.start_date = start_date
            od.end_date = start_date + proposal_duration
            session.commit()

        utils.log_action(
            f"Modify proposal start date for {account_name} to {start_date}"
        )

    def date_investment(self, account_name, date, inv_id) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Date should be valid
        start_date = utils.unwrap_if_right(utils.check_date_valid(date))

        # Update row in database
        with Session() as session:
            od = session.query(Investor).filter_by(id=inv_id, account=account_name)
            if od:
                od.start_date = start_date
                od.end_date = start_date + timedelta(days=1825)
                session.commit()

        utils.log_action(
            f"Modify investment start date for investment #{inv_id} for account {account_name} to {start_date}"
        )

    def check_sus_limit(self, account_name) -> None:
        # This is a complicated function, the steps:
        # 1. Get proposal for account and compute the total SUs from proposal
        # 2. Determine the current usage for the user across clusters
        # 3. Add any investment SUs to the total, archiving any exhausted investments
        # 4. Add archived investments associated to the current proposal

        session = Session()

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Compute the Total SUs for the proposal period
        proposal_row = session.query(Proposal).filter_by(account=account_name).first()
        total_sus = sum([getattr(proposal_row, cluster) for cluster in app_settings.clusters])

        # Parse the used SUs for the proposal period
        used_sus_per_cluster = Account(account_name).get_raw_usage(*app_settings.clusters, in_hours=True)
        used_sus = sum(used_sus_per_cluster.values())

        # Compute the sum of investment SUs, archiving any exhausted investments
        investor_rows = session.query(Investor).find(account=account_name).all()
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
                    account=account_name,
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

        notification_percent = utils.PercentNotified(proposal_row.percent_notified)
        if notification_percent == utils.PercentNotified.Hundred:
            exit(
                f"{datetime.now()}: Skipping account {account_name} because it should have already been notified and locked"
            )

        percent_usage = 100.0 * used_sus / total_sus

        # Update percent_notified in the table and notify account owner if necessary
        updated_notification_percent = utils.find_next_notification(percent_usage)
        if updated_notification_percent != notification_percent:
            proposal_row.percent_notified = updated_notification_percent.value
            utils.notify_sus_limit(account_name)

            utils.log_action(
                f"Updated proposal percent_notified to {updated_notification_percent} for {account_name}"
            )

        # Lock the account if necessary
        if updated_notification_percent == utils.PercentNotified.Hundred:
            if account_name != "root":
                Account(account_name).set_locked_state(True)

                utils.log_action(
                    f"The account for {account_name} was locked due to SUs limit"
                )

        session.commit()
        session.close()

    def check_proposal_end_date(self, account_name) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        proposal_row = Session().query(Proposal).filter_by(account=account_name).first()
        today = date.today()
        three_months_before_end_date = proposal_row.end_date - timedelta(days=90)

        if today == three_months_before_end_date:
            utils.three_month_proposal_expiry_notification(account_name)
        elif today == proposal_row.end_date:
            utils.proposal_expires_notification(account_name)
            Account(account_name).set_locked_state(True)
            utils.log_action(
                f"The account for {account_name} was locked because it reached the end date {proposal_row.end_date}"
            )

    def get_sus(self, account_name) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        proposal_row = Session().query(Proposal).filter_by(account=account_name).first()

        print(f"type,{','.join(app_settings.clusters)}")
        sus = [str(getattr(proposal_row, c)) for c in app_settings.clusters]
        print(f"proposal,{','.join(sus)}")

        investor_sus = utils.get_current_investor_sus(account_name)
        for row in investor_sus:
            print(f"investment,{row}")

    def dump(self, proposal: str, investor: str, proposal_archive: str, investor_archive: str) -> None:
        proposal_p = Path(proposal)
        investor_p = Path(investor)
        proposal_archive_p = Path(proposal_archive)
        investor_archive_p = Path(investor_archive)
        paths = (proposal_p, investor_p, investor_archive_p, proposal_archive_p)

        if any(p.exists() for p in paths):
            exit(
                f"ERROR: Neither {proposal_p}, {investor_p}, {proposal_archive_p}, nor {investor_archive_p} can exist.")

        with Session() as session:
            tables = (Proposal, ProposalArchive, Investor, InvestorArchive)
            for table, path in zip(tables, paths):
                utils.freeze_if_not_empty(session.query(table).all(), path)

    def withdraw(self, account_name, sus) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Service units should be a valid number
        sus_to_withdraw = utils.unwrap_if_right(
            utils.check_service_units_valid(sus)
        )

        # First check if the user has enough SUs to withdraw
        available_investments = sum(utils.get_available_investor_sus(account_name))

        should_exit = False
        if sus_to_withdraw > available_investments:
            should_exit = True
            print(
                f"Requested to withdraw {sus_to_withdraw[c]} on cluster {c} but the account only has {available_investments[c]} SUs to withdraw from on this cluster!"
            )
        if should_exit:
            exit()

        # Go through investments, oldest first and start withdrawing
        investments = Session().query(Investor).filter_by(account=account_name).all()
        for idx, investment in enumerate(investments):
            to_withdraw = 0
            investment_remaining = investment.service_units - investment.withdrawn_sus

            # If not SUs to withdraw, skip the proposal entirely
            if investment_remaining == 0:
                print(
                    f"No service units can be withdrawn from investment {investment['id']}"
                )
                continue

            # Determine what we can withdraw from current investment
            if sus_to_withdraw > investment_remaining:
                to_withdraw = investment_remaining
                sus_to_withdraw -= investment_remaining
            else:
                to_withdraw = sus_to_withdraw
                sus_to_withdraw = 0

            # Update the current investment and log withdrawal
            with Session() as session:
                investment.current_sus += to_withdraw
                investment.withdrawn_sus += to_withdraw
                session.commit()

            utils.log_action(
                f"Withdrew from investment {investment['id']} for account {account_name} with value {to_withdraw}"
            )

            # Determine if we are done processing investments
            if sus_to_withdraw == 0:
                print(f"Finished withdrawing after {idx} iterations")
                break

    def check_proposal_violations(self) -> None:
        # Iterate over all of the proposals looking for proposal violations
        proposals = Session().query(Proposal).all()

        for proposal in proposals:
            investments = sum(utils.get_available_investor_sus(proposal.account))

            subtract_previous_investment = 0
            cluster_sus = Account(proposal.account).get_raw_usage(*app_settings.clusters, in_hours=True)
            for cluster, used_sus in cluster_sus.items():
                avail_sus = getattr(proposal, cluster)
                if used_sus > (avail_sus + investments - subtract_investment):
                    print(
                        f"Account {proposal.account}, Cluster {cluster}, Used SUs {used_sus}, Avail SUs {avail_sus}, Investment SUs {investments[cluster]}"
                    )
                if used_sus > avail_sus:
                    subtract_previous_investment += investments - used_sus

    def usage(self, account_name) -> None:

        account = Account(account_name)
        account.check_has_proposal()
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        print(account.usage_string())

    def renewal(self, account_name, **sus) -> None:

        session = Session()

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Account associations better exist!
        account = Account(account_name)
        account.raise_missing_cluster_associations()

        # Make sure SUs are valid
        # Service units should be a valid number
        utils.check_service_units_valid_clusters(sus)

        # Archive current proposal, recording the usage on each cluster
        current_proposal = session.query(Proposal).filter_by(account=account_name).first()
        proposal_id = current_proposal.id

        current_usage = account.get_raw_usage(*app_settings.clusters, in_hours=True)
        to_insert = {f"{c}_usage": current_usage[c] for c in app_settings.clusters}
        for key in ["account", "start_date", "end_date"] + app_settings.clusters:
            to_insert[key] = getattr(current_proposal, key)
        session.add(ProposalArchive(**to_insert))

        # Archive any investments which are
        # - past their end_date
        # - withdraw + renewal leaves no current_sus and fully withdrawn account
        investor_rows = session.query(Investor).filter_by(account=account_name).all()
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
                    "account": account_name,
                    "proposal_id": current_proposal.id,
                    "investor_id": investor_row.id,
                }
                session.add(InvestorArchive(**to_insert))
                investor_row.delete()

        # Renewal, should exclude any previously rolled over SUs
        current_investments = sum(
            utils.get_current_investor_sus_no_rollover(account_name)
        )

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
                investor_rows = session.query(Investor).filter_by(account=account_name).all()
                for investor_row in investor_rows:
                    if need_to_rollover > 0:
                        to_withdraw = (investor_row.service_units - investor_row.withdrawn_sus) // utils.years_left(
                            investor_row.end_date)
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
        proposal_type = utils.ProposalType(current_proposal.proposal_type)
        proposal_duration = utils.get_proposal_duration(proposal_type)
        start_date = date.today()
        end_date = start_date + proposal_duration

        prop = session.query(Proposal).filter_by(id=proposal_id).all()
        prop.percent_notified = utils.PercentNotified.Zero.value
        prop.start_date = start_date
        prop.end_date = end_date
        for c in app_settings.clusters:
            setattr(prop, c, sus[c])

        # Set RawUsage to zero and unlock the account
        account.reset_raw_usage()
        account.set_locked_state(False)

        session.commit()
        session.close()

    def import_proposal(self, path, overwrite=False) -> None:
        utils.import_from_json(path, Proposal, overwrite)

    def import_investor(self, path, overwrite=False) -> None:
        utils.import_from_json(path, Investor, overwrite)

    @RequireRoot
    def release_hold(self, account_name: str) -> None:
        """Release the hold on a user account

        Args:
            account_name: The name of the account
        """

        account = Account(account_name)
        account.check_has_proposal(raise_if=True)
        Account(account_name).set_locked_state(False)

    def alloc_sus(self, path: Path) -> None:
        """Export allocated service units to a CSV file

        Args:
            path: The path to write exported data to
        """

        with path.open("w") as fp, Session() as session:
            fp.write("account,smp,gpu,mpi,htc\n")
            for proposal in session.query(Proposal).all():
                fp.write(f"{proposal.account},{proposal.smp},{proposal.gpu},{proposal.mpi},{proposal.htc}\n")

    @RequireRoot
    def reset_raw_usage(self, account_name: str) -> None:
        """Reset raw usage for the given account

        Args:
            account_name: The name of the account to reset
        """

        account = Account(account_name)
        account.check_has_proposal(raise_if=True)
        account.reset_raw_usage()

    def find_unlocked(self) -> None:
        """Print the names for all unlocked, unexpired accounts"""

        today = date.today()
        for proposal in Session().query(Proposal).all():
            is_locked = Account(proposal.account).get_locked_state()
            if (not is_locked) and proposal.end_date < today:
                print(proposal.account)

    @RequireRoot
    def lock_with_notification(self, account_name: str) -> None:
        """Lock the specified user account and send a proposal expiration email

        Args:
            account_name: The name of the account to lock
        """

        account = Account(account_name)
        account.check_has_proposal(raise_if=True)
        account.set_locked_state(True)
        account.proposal_expires_notification()
