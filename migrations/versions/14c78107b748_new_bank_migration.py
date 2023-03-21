"""New Bank Migration

Revision ID: 14c78107b748
Revises:
Create Date: 2023-02-21 09:41:01.940279

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"

# revision identifiers, used by Alembic.
revision = '14c78107b748'
down_revision = None
branch_labels = None
depends_on = None


def print_tables(connection):
    metadata = sa.MetaData()
    metadata.reflect(connection.engine)
    insp = sa.inspect(connection.engine)
    for table_name in metadata.tables:
        print(f'\n{table_name} -------------------------')
        for column in insp.get_columns(table_name):
            for name, value in column.items():
                print('  ', end='')
                if value:
                    field = name if value in [True, 'auto'] else value
                    print(field, end=' ')
            print()

    print("\n.\n.\n.\n")


def upgrade():
    """Upgrade the database schema to the next version"""

    conn = op.get_bind()

    # TODO: these already exist in this context?
    op.drop_table('account')
    op.drop_table('investment')
    op.drop_table('allocation')

    # Concatenate tables with their archives
    # proposal + proposal_archive -> _proposal_old
    conn.execute("INSERT INTO proposal (start_date, end_date, smp, mpi, htc, gpu, account) "
                 "SELECT start_date, end_date, smp, mpi, htc, gpu, account "
                 "FROM proposal_archive")

    conn.execute("UPDATE proposal "
                 "SET percent_notified=0 "
                 "WHERE percent_notified is NULL")

    op.drop_column('proposal', 'proposal_type')
    op.rename_table('proposal', '_proposal_old')

    # investor + investor_archive -> _investment_old
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

    op.drop_column('investor', 'proposal_type')
    op.rename_table('investor', '_investment_old')

    # Drop old tables after concatenation
    for table in ('investor_archive', 'proposal_archive'):
        op.drop_table(table)

    # Create Account Table
    op.create_table(
        'account',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False, unique=True)
    )

    # Exclusive OR account names from investment/proposal tables to populate account table
    # TODO: look into sqlalchemy representation of this?
    conn.execute("INSERT INTO account (name) "
                 "SELECT DISTINCT _proposal_old.account "
                 "FROM _proposal_old "
                 "LEFT JOIN _investment_old ON _proposal_old.account = _investment_old.account "
                 "WHERE _investment_old.account IS NULL "
                 "UNION ALL "
                 "SELECT DISTINCT _investment_old.account "
                 "FROM _investment_old "
                 "LEFT JOIN _proposal_old ON _proposal_old.account=_investment_old.account "
                 "WHERE _proposal_old.account IS NULL")

    # Create Proposal Table
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

    # Create Investment Table
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

    accounts = conn.execute("SELECT * from account").fetchall()
    for account in accounts:
        old_investments = conn.execute(f"SELECT * from _investment_old WHERE _investment_old.account='{account.name}'").fetchall()
        old_proposals = conn.execute(f"SELECT * from _proposal_old WHERE _proposal_old.account='{account.name}'").fetchall()
        #TODO: sort by date?
        new_proposals = []
        for old_proposal in old_proposals:
            allocs = []
            for cluster_name in ['smp','mpi','gpu','htc']:
                allocs.append({'proposal_id': old_proposal.id,
                               'cluster_name': cluster_name,
                               'service_units_total': getattr(old_proposal, cluster_name)}
                              )
                # TODO: no need to set service_units_used, defaults to 0, updated by first run of new bank code?
            new_proposal = {'id': old_proposal.id,
                            'account_id': account.id,
                            'start_date': datetime.strptime(old_proposal.start_date, DATE_FORMAT),
                            'end_date': datetime.strptime(old_proposal.end_date, DATE_FORMAT),
                            'percent_notified': old_proposal.percent_notified}
            op.bulk_insert(allocation_table, allocs)
            new_proposals.append(new_proposal)
        op.bulk_insert(proposal_table, new_proposals)

        new_investments = []
        for old_investment in old_investments:
            new_investment = {'id': old_investment.id,
                              'account_id': account.id,
                              'start_date': datetime.strptime(old_investment.start_date, DATE_FORMAT),
                              'end_date': datetime.strptime(old_investment.start_date, DATE_FORMAT),
                              'service_units': old_investment.service_units,
                              'rollover_sus': old_investment.rollover_sus,
                              'withdrawn_sus': old_investment.withdrawn_sus,
                              'current_sus': old_investment.current_sus}
            new_investments.append(new_investment)
        op.bulk_insert(investment_table, new_investments)

    op.drop_table('_proposal_old')
    op.drop_table('_investment_old')

def downgrade():
    """Downgrade the database schema to the previous version"""

    raise NotImplementedError(
        'Rollbacks for this version are not supported. '
        'Data has been dropped in the upgrade that cannot be recovered. '
        'Restore a file system snapshot instead.'
    )