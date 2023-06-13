"""System refactor migration

Revision ID: a6c26a203bd1
Revises:
Create Date: 2022-02-21 15:01:03.939907
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a6c26a203bd1'
down_revision = None
branch_labels = None
depends_on = None

# New enum value introduced for proposal types
PROPOSAL_TYPE_ENUM_NAME = 'proposalenum'
PROPOSAL_TYPE = 'Proposal'
CLASS_TYPE = 'Class'
UNKNOWN_TYPE = 'Unknown'

# Map old percent notified enum values to their new int representations
PERCENT_NOTIFIED_MAPPER = {
    0: 0,
    1: 25,
    2: 50,
    3: 75,
    4: 90,
    5: 100}


def upgrade():
    """Upgrade the database schema to the next version"""

    proposal_type_col_type = sa.Enum(UNKNOWN_TYPE, PROPOSAL_TYPE, CLASS_TYPE, name=PROPOSAL_TYPE_ENUM_NAME)
    with op.batch_alter_table("proposal", recreate='always') as proposal_table:
        proposal_table.alter_column('account', new_column_name='account_name', existing_type=sa.TEXT(), type_=sa.String(), nullable=False)
        proposal_table.alter_column('start', existing_type=sa.DATE(), nullable=False)
        proposal_table.alter_column('end', existing_type=sa.DATE(), nullable=False)
        proposal_table.alter_column('percent_notified', existing_type=sa.INTEGER(), nullable=False)
        proposal_table.alter_column('proposal_type', existing_type=sa.INTEGER(), type_=proposal_type_col_type, nullable=True)

    # Change percent notified values from enum type values to actual notification percentage
    op.execute(
        'UPDATE proposal SET proposal_type = (CASE '
        f'WHEN proposal_type = 0 THEN "{PROPOSAL_TYPE}" '
        f'WHEN proposal_type = 1 THEN "{CLASS_TYPE}" '
        'END)')

    # Change percent notified values from enum type values to actual notification percentage
    op.execute(
        'UPDATE proposal SET percent_notified = (CASE '
        f'WHEN percent_notified = 0 THEN {PERCENT_NOTIFIED_MAPPER[0]} '
        f'WHEN percent_notified = 1 THEN {PERCENT_NOTIFIED_MAPPER[1]} '
        f'WHEN percent_notified = 2 THEN {PERCENT_NOTIFIED_MAPPER[2]} '
        f'WHEN percent_notified = 3 THEN {PERCENT_NOTIFIED_MAPPER[3]} '
        f'WHEN percent_notified = 4 THEN {PERCENT_NOTIFIED_MAPPER[4]} '
        f'WHEN percent_notified = 5 THEN {PERCENT_NOTIFIED_MAPPER[5]} '
        'END)')

    with op.batch_alter_table("proposal_archive", recreate='always') as p_archive_table:
        p_archive_table.alter_column('account', new_column_name='account_name', existing_type=sa.TEXT(), type_=sa.String(), nullable=False)
        p_archive_table.alter_column('end', existing_type=sa.DATE(), nullable=False)
        p_archive_table.alter_column('gpu', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('gpu_usage', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('htc', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('htc_usage', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('mpi', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('mpi_usage', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('smp', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('smp_usage', existing_type=sa.INTEGER(), nullable=False)
        p_archive_table.alter_column('start', existing_type=sa.DATE(), nullable=False)
        p_archive_table.add_column(sa.Column('proposal_type', proposal_type_col_type, nullable=True))

    # The original table does not track the proposal type, so we fill in missing values before settings nullable=False
    op.execute(f'UPDATE proposal_archive SET proposal_type = "{UNKNOWN_TYPE}"')
    with op.batch_alter_table("proposal_archive", recreate='always') as p_archive_table:
        p_archive_table.alter_column('proposal_type', nullable=False)

    with op.batch_alter_table("investor", recreate='always') as investor_table:
        investor_table.alter_column('account', new_column_name='account_name', existing_type=sa.TEXT(), type_=sa.String(), nullable=False)
        investor_table.alter_column('current_sus', existing_type=sa.INTEGER(), nullable=False)
        investor_table.alter_column('end', existing_type=sa.DATE(), nullable=False)
        investor_table.alter_column('rollover_sus', type=sa.INTEGER(), nullable=False)
        investor_table.alter_column('service_units', existing_type=sa.INTEGER(), nullable=False)
        investor_table.alter_column('start', existing_type=sa.DATE(), nullable=False)
        investor_table.alter_column('withdrawn_sus', existing_type=sa.INTEGER(), nullable=False)
        investor_table.drop_column('proposal_type')

    with op.batch_alter_table("investor_archive", recreate='always') as inv_archive_table:
        inv_archive_table.alter_column('account', new_column_name='account_name', existing_type=sa.TEXT(), type_=sa.String(), nullable=False)
        inv_archive_table.alter_column('current_sus', existing_type=sa.INTEGER(), nullable=False)
        inv_archive_table.alter_column('end', existing_type=sa.DATE(), nullable=False)
        inv_archive_table.alter_column('exhaustion_date', existing_type=sa.DATE(), nullable=False)
        inv_archive_table.alter_column('service_units', existing_type=sa.INTEGER(), nullable=False)
        inv_archive_table.alter_column('start', existing_type=sa.DATE(), nullable=False)
        inv_archive_table.drop_column('proposal_id')
        inv_archive_table.drop_column('investor_id')


def downgrade():
    """Downgrade the database schema to the previous version"""

    raise NotImplementedError(
        'Rollbacks for this version are not supported. '
        'Data has been dropped in the upgrade that cannot be recovered. '
        'Restore a file system snapshot instead.'
    )
