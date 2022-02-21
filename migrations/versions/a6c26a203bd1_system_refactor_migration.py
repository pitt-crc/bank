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


def upgrade():
    op.add_column('proposal', sa.Column('account_name', sa.String(), nullable=False))
    op.alter_column('proposal', 'end_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('proposal', 'percent_notified', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal', 'proposal_type', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal', 'start_date', existing_type=sa.DATE(), nullable=False)
    op.drop_column('proposal', 'account')

    op.add_column('proposal_archive', sa.Column('account_name', sa.String(), nullable=False))
    op.add_column('proposal_archive', sa.Column('proposal_type', sa.Enum('Proposal', 'Class', name='proposalenum'), nullable=False))
    op.alter_column('proposal_archive', 'end_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('proposal_archive', 'gpu', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'gpu_usage', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'htc', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'htc_usage', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'mpi', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'mpi_usage', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'smp', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'smp_usage', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('proposal_archive', 'start_date', existing_type=sa.DATE(), nullable=False)
    op.drop_column('proposal_archive', 'account')

    op.add_column('investor', sa.Column('account_name', sa.String(), nullable=False))
    op.alter_column('investor', 'current_sus', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('investor', 'end_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('investor', 'rollover_sus', type=sa.INTEGER(), nullable=False)
    op.alter_column('investor', 'service_units', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('investor', 'start_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('investor', 'withdrawn_sus', existing_type=sa.INTEGER(), nullable=False)
    op.drop_column('investor', 'account')
    op.drop_column('investor', 'proposal_type')

    op.add_column('investor_archive', sa.Column('account_name', sa.String(), nullable=False))
    op.alter_column('investor_archive', 'current_sus', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('investor_archive', 'end_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('investor_archive', 'exhaustion_date', existing_type=sa.DATE(), nullable=False)
    op.alter_column('investor_archive', 'service_units', existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('investor_archive', 'start_date', existing_type=sa.DATE(), nullable=False)
    op.drop_column('investor_archive', 'proposal_id')
    op.drop_column('investor_archive', 'account')
    op.drop_column('investor_archive', 'investor_id')


def downgrade():
    op.add_column('proposal', sa.Column('account', sa.TEXT(), nullable=True))
    op.alter_column('proposal', 'start_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('proposal', 'proposal_type', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal', 'percent_notified', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal', 'end_date', existing_type=sa.DATE(), nullable=True)
    op.drop_column('proposal', 'account_name')

    op.add_column('proposal_archive', sa.Column('account', sa.TEXT(), nullable=True))
    op.alter_column('proposal_archive', 'start_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('proposal_archive', 'smp_usage', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'smp', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'mpi_usage', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'mpi', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'htc_usage', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'htc', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'gpu_usage', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'gpu', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('proposal_archive', 'end_date', existing_type=sa.DATE(), nullable=True)
    op.drop_column('proposal_archive', 'proposal_type')
    op.drop_column('proposal_archive', 'account_name')

    op.add_column('investor', sa.Column('proposal_type', sa.INTEGER(), nullable=True))
    op.add_column('investor', sa.Column('account', sa.TEXT(), nullable=True))
    op.alter_column('investor', 'withdrawn_sus', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('investor', 'start_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('investor', 'service_units', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('investor', 'rollover_sus', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('investor', 'end_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('investor', 'current_sus', existing_type=sa.INTEGER(), nullable=True)
    op.drop_column('investor', 'account_name')

    op.add_column('investor_archive', sa.Column('investor_id', sa.INTEGER(), nullable=True))
    op.add_column('investor_archive', sa.Column('account', sa.TEXT(), nullable=True))
    op.add_column('investor_archive', sa.Column('proposal_id', sa.INTEGER(), nullable=True))
    op.alter_column('investor_archive', 'start_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('investor_archive', 'service_units', existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('investor_archive', 'exhaustion_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('investor_archive', 'end_date', existing_type=sa.DATE(), nullable=True)
    op.alter_column('investor_archive', 'current_sus', existing_type=sa.INTEGER(), nullable=True)
    op.drop_column('investor_archive', 'account_name')
