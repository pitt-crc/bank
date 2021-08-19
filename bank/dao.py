import json
from datetime import date, datetime, timedelta
from math import ceil
from os import geteuid
from pathlib import Path

from bank import utils
from bank.orm import Investor, InvestorArchive, Proposal, ProposalArchive, Session
from bank.settings import app_settings


class Bank:
    def insert(self, prop_type, account_name, smp, mpi, gpu, htc) -> None:
        # Account shouldn't exist in the proposal table already
        if Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Proposal for account `{account_name}` already exists. Exiting...")

        # Account associations better exist!
        _ = utils.unwrap_if_right(
            utils.account_and_cluster_associations_exists(account_name)
        )

        # Make sure we understand the proposal type
        proposal_type = utils.unwrap_if_right(utils.parse_proposal_type(prop_type))
        proposal_duration = utils.get_proposal_duration(proposal_type)
        start_date = date.today()

        # Service units should be a valid number
        sus = {'smp': smp, 'htc': htc, 'mpi': mpi, 'gpu': gpu}
        utils.check_service_units_valid_clusters(sus)

        new_proposal = Proposal(
            account=account_name,
            proposal_type=proposal_type.value,
            percent_notified=utils.PercentNotified.Zero.value,
            start_date=start_date,
            end_date=start_date + proposal_duration,
            **{c: sus[c] for c in app_settings.clusters}
        )

        with Session() as session:
            session.add(new_proposal)
            session.commit()

        utils.log_action(
            f"Inserted proposal with type {proposal_type.name} for {account_name} with `{sus['smp']}` on SMP, `{sus['mpi']}` on MPI, `{sus['gpu']}` on GPU, and `{sus['htc']}` on HTC"
        )

    def investor(self, account_name, sus) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Account associations better exist!
        _ = utils.unwrap_if_right(
            utils.account_and_cluster_associations_exists(account_name)
        )

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

    def info(self, account_name: str) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        proposal = Session().query(Proposal).filter_by(account=account_name).first()

        # Get entire row, convert to human readable columns
        od = dict(proposal)
        od["proposal_type"] = utils.ProposalType(od["proposal_type"]).name
        od["percent_notified"] = utils.PercentNotified(od["percent_notified"]).name
        od["start_date"] = od["start_date"].strftime("%m/%d/%y")
        od["end_date"] = od["end_date"].strftime("%m/%d/%y")

        print("Proposal")
        print("--------")
        print(json.dumps(od, indent=2))
        print()

        if not Investor.check_matching_entry_exists(account=account_name):
            exit()

        investors = Session().query(Investor).filter_by(account=account_name).all()
        for investor in investors:
            od = dict(investor)
            od["proposal_type"] = utils.ProposalType(od["proposal_type"]).name
            od["start_date"] = od["start_date"].strftime("%m/%d/%y")
            od["end_date"] = od["end_date"].strftime("%m/%d/%y")

            print(f"Investment: {od['id']:3}")
            print(f"---------------")
            print(json.dumps(od, indent=2))
            print()

    def modify(self, account_name, smp, mpi, gpu, htc) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        sus = {'smp': smp, 'htc': htc, 'mpi': mpi, 'gpu': gpu}
        utils.check_service_units_valid_clusters(sus)

        # Update row in database
        with Session() as session:
            od = session.query(Proposal).filter_by(account=account_name).first()
            proposal_duration = utils.get_proposal_duration(
                utils.ProposalType(od.proposal_type)
            )
            start_date = date.today()
            end_date = start_date + proposal_duration
            od.start_date = start_date
            od.end_date = end_date
            for clus in app_settings.clusters:
                setattr(od, clus, sus[clus])

            session.commit()

        utils.log_action(
            f"Modified proposal for {account_name} with `{sus['smp']}` on SMP, `{sus['mpi']}` on MPI, `{sus['gpu']}` on GPU, and `{sus['htc']}` on HTC"
        )

    def add(self, account_name, smp, mpi, gpu, htc) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        sus = {'smp': smp, 'htc': htc, 'mpi': mpi, 'gpu': gpu}
        utils.check_service_units_valid_clusters(sus, greater_than_ten_thousand=False)

        # Update row in database
        with Session() as session:
            od = session.query(Proposal).filter_by(account=account_name)
            for clus in app_settings.clusters:
                new_su = getattr(od, clus) + sus[clus]
                setattr(od, clus, new_su)

            session.commit()

        utils.log_action(
            f"Added SUs to proposal for {account_name}, new limits are `{od['smp']}` on SMP, `{od['mpi']}` on MPI, `{od['gpu']}` on GPU, and `{od['htc']}` on HTC"
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
        used_sus_per_cluster = {c: 0 for c in app_settings.clusters}
        for cluster in app_settings.clusters:
            used_sus_per_cluster[cluster] = utils.get_raw_usage_in_hours(
                account_name, cluster
            )
        used_sus = sum(used_sus_per_cluster.values())

        # Compute the sum of investment SUs, archiving any exhausted investments
        investor_rows = session.query(Investor).find(account=account_name).all()
        sum_investment_sus = 0
        for investor_row in investor_rows:
            # Check if investment is exhausted
            exhausted = False
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
                exhausted[cluster] = True

            if exhausted:
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
                session.add(InvestorArchive)
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
                utils.lock_account(account_name)

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
            utils.lock_account(account_name)
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
            for cluster in app_settings.clusters:
                avail_sus = getattr(proposal, cluster)
                used_sus = utils.get_raw_usage_in_hours(proposal.account, cluster)
                if used_sus > (avail_sus + investments - subtract_investment):
                    print(
                        f"Account {proposal.account}, Cluster {cluster}, Used SUs {used_sus}, Avail SUs {avail_sus}, Investment SUs {investments[cluster]}"
                    )
                if used_sus > avail_sus:
                    subtract_previous_investment += investments - used_sus

    def usage(self, account_name) -> None:
        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        print(utils.usage_string(account_name))

    def renewal(self, account_name, smp, mpi, gpu, htc) -> None:

        session = Session()

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Account associations better exist!
        _ = utils.unwrap_if_right(
            utils.account_and_cluster_associations_exists(account_name)
        )

        # Make sure SUs are valid
        # Service units should be a valid number
        sus = {'smp': smp, 'htc': htc, 'mpi': mpi, 'gpu': gpu}
        utils.check_service_units_valid_clusters(sus)

        # Archive current proposal, recording the usage on each cluster
        current_proposal = session.query(Proposal).filter_by(account=account_name).first()
        proposal_id = current_proposal.id
        current_usage = {
            c: utils.get_raw_usage_in_hours(account_name, c) for c in app_settings.clusters
        }
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

        # Set RawUsage to zero
        utils.reset_raw_usage(account_name)

        # Unlock the account
        utils.unlock_account(account_name)

        session.commit()
        session.close()

    def import_proposal(self, path, overwrite=False) -> None:
        utils.import_from_json(path, Proposal, overwrite)

    def import_investor(self, path, overwrite=False) -> None:
        utils.import_from_json(path, Investor, overwrite)

    def release_hold(self, account_name) -> None:
        if geteuid() != 0:
            exit("ERROR: `release_hold` should be run with sudo privileges")

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Unlock the account
        utils.unlock_account(account_name)

    def alloc_sus(self) -> None:
        alloc_sus = 0
        with open("service_units.csv", "w") as fp, Session() as session:
            fp.write("account,smp,gpu,mpi,htc\n")
            for proposal in session.query(Proposal).all():
                fp.write(
                    f"{proposal.account},{proposal.smp},{proposal.gpu},{proposal.mpi},{proposal.htc}\n"
                )

                alloc_sus += sum([proposal[c] for c in app_settings.clusters])

        print(alloc_sus)

    def reset_raw_usage(self, account_name) -> None:
        if geteuid() != 0:
            exit("ERROR: `reset_raw_usage` should be run with sudo privileges")

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Unlock the account
        utils.reset_raw_usage(account_name)

    def find_unlocked(self) -> None:
        today = date.today()
        for proposal in Session().query(Proposal).all():
            is_locked = utils.is_account_locked(proposal.account)
            if (not is_locked) and proposal.end_date < today:
                print(proposal.account)

    def lock_with_notification(self, account_name: str) -> None:
        if geteuid() != 0:
            exit("ERROR: `lock_with_notification` should be run with sudo privileges")

        # Account must exist in database
        if not Proposal.check_matching_entry_exists(account=account_name):
            exit(f"Account `{account_name}` doesn't exist in the database")

        # Unlock the account
        utils.proposal_expires_notification(account_name)
        utils.lock_account(account_name)
