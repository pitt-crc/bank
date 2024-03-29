"""New Bank Migration

Revision ID: 14c78107b748
Revises:
Create Date: 2023-02-21 09:41:01.940279
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

from bank.system import SlurmAccount
from bank.exceptions import AccountNotFoundError

DATE_FORMAT = "%Y-%m-%d"

# revision identifiers, used by Alembic.
revision = '14c78107b748'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade the database schema to the next version"""

    conn = op.get_bind()

    num_investments = conn.execute("SELECT count(*) FROM investor").fetchall()
    num_inv_archive = conn.execute("SELECT count(*) FROM investor_archive").fetchall()
    num_investments_old = num_investments[0][0] + num_inv_archive[0][0]

    # Concatenate proposal table with archive
    conn.execute("INSERT INTO proposal (start_date, end_date, smp, mpi, htc, gpu, account) "
                 "SELECT start_date, end_date, smp, mpi, htc, gpu, account "
                 "FROM proposal_archive")

    conn.execute("UPDATE proposal "
                 "SET percent_notified=100 "
                 "WHERE percent_notified is NULL")

    # Drop the proposal archive and rename the combined table
    op.drop_table('proposal_archive')
    op.rename_table('proposal', '_proposal_old')

    # Concatenate investor tabled with archive
    conn.execute(
        "INSERT INTO investor (start_date, end_date, service_units, current_sus, account) "
        "SELECT start_date, end_date, service_units, current_sus, account "
        "FROM investor_archive")

    conn.execute("UPDATE investor "
                 "SET withdrawn_sus=-9 "
                 "WHERE withdrawn_sus is NULL")

    conn.execute("UPDATE investor "
                 "SET rollover_sus=-9 "
                 "WHERE rollover_sus is NULL")

    # Drop the investor archive and renamed the combined table
    op.drop_table('investor_archive')
    op.rename_table('investor', '_investment_old')

    # Create Account Table
    account_table = op.create_table(
        'account',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False, unique=True)
    )

    # Populate account table with all distinct account names from investment/proposal tables
    conn.execute("INSERT INTO account (name) "
                 "SELECT account FROM"
                 "(SELECT DISTINCT _proposal_old.account "
                 "FROM _proposal_old "
                 "UNION "
                 "SELECT DISTINCT _investment_old.account "
                 "FROM _investment_old)")

    # Create proposal table with new schema and account id foreign key
    proposal_table = op.create_table(
        'proposal',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('account_id', sa.Integer, sa.ForeignKey("account.id")),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('percent_notified', sa.Integer, nullable=False)
    )

    # Create Allocation Table
    allocation_table = op.create_table(
        'allocation',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('proposal_id', sa.Integer, sa.ForeignKey("proposal.id")),
        sa.Column('cluster_name', sa.String, nullable=False),
        sa.Column('service_units_total', sa.Integer, nullable=False),
        sa.Column('service_units_used', sa.Integer, nullable=False, default=0)
    )

    # Create investment table with new schema and account id foreign key
    investment_table = op.create_table(
        'investment',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('account_id', sa.Integer, sa.ForeignKey("account.id")),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('service_units', sa.Integer, nullable=False),
        sa.Column('rollover_sus', sa.Integer, nullable=False),
        sa.Column('withdrawn_sus', sa.Integer, nullable=False),
        sa.Column('current_sus', sa.Integer, nullable=False)
    )

    # For each account, create new schema proposals and investments from entries in old schema
    accounts = conn.execute("SELECT * from account").fetchall()
    for account in accounts:

        # Attempt to set up the SLURM account, skipping if it does not exist
        try:
            slurm_acct = SlurmAccount(account.name)
        except AccountNotFoundError:
            print(f"SLURM Account for {account.name} does not exist, skipping...\n")
            continue

        old_investments = conn.execute(f"SELECT * from _investment_old WHERE _investment_old.account='{account.name}'").fetchall()
        old_proposals = conn.execute(f"SELECT * from _proposal_old WHERE _proposal_old.account='{account.name}'").fetchall()
        new_proposals = []
        for prop in old_proposals:

            # Determine whether the proposal has more than a standard allocation, creating a floating alloc if not
            allocs = []
            total_sus = 0

            for cluster_name in ['smp','mpi','gpu','htc']:
                total_sus += getattr(prop, cluster_name)
                allocs.append({'proposal_id': prop.id,
                               'cluster_name': cluster_name,
                               'service_units_total': getattr(prop, cluster_name),
                               'service_units_used': slurm_acct.get_cluster_usage_total(cluster_name, in_hours=True)}
                              )

            # Empty the allocations and establish a standard allocation
            if total_sus <= 25000:
                allocs = [{'proposal_id': prop.id,
                           'cluster_name': 'all_clusters',
                           'service_units_total': 25000}]

            new_proposal = {'id': prop.id,
                            'account_id': account.id,
                            'start_date': datetime.strptime(prop.start_date, DATE_FORMAT),
                            'end_date': datetime.strptime(prop.end_date, DATE_FORMAT),
                            'percent_notified': prop.percent_notified}

            op.bulk_insert(allocation_table, allocs)
            new_proposals.append(new_proposal)

        op.bulk_insert(proposal_table, new_proposals)

        new_investments = []
        for inv in old_investments:
            new_investment = {'id': inv.id,
                              'account_id': account.id,
                              'start_date': datetime.strptime(inv.start_date, DATE_FORMAT),
                              'end_date': datetime.strptime(inv.start_date, DATE_FORMAT),
                              'service_units': inv.service_units,
                              'rollover_sus': inv.rollover_sus,
                              'withdrawn_sus': inv.withdrawn_sus,
                              'current_sus': inv.current_sus}
            new_investments.append(new_investment)

        op.bulk_insert(investment_table, new_investments)

    num_new_investments = conn.execute("SELECT count(*) FROM investment").fetchall()
    assert num_new_investments[0][0] == num_investments_old, "The number of new investments must equal the number of old investments"

    # Drop old schema tables
    op.drop_table('_proposal_old')
    op.drop_table('_investment_old')


def downgrade():
    """Downgrade the database schema to the previous version"""

    raise NotImplementedError(
        'Rollbacks for this version are not supported. '
        'Data has been dropped in the upgrade that cannot be recovered. '
        'Restore a file system snapshot instead.'
    )
