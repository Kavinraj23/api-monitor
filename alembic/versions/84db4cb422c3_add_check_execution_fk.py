"""add check execution fk

Revision ID: 84db4cb422c3
Revises: 
Create Date: 2025-12-31 23:42:39.036298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '84db4cb422c3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'checks',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('required_fields', sa.JSON(), nullable=False),
        sa.Column('expected_status_code', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('latency_threshold_ms', sa.Integer(), nullable=True),
        sa.Column('interval_minutes', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_checks_id'), 'checks', ['id'], unique=False)

    op.create_table(
        'check_executions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('check_id', sa.Integer(), sa.ForeignKey('checks.id'), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('missing_fields', sa.JSON(), nullable=True),
        sa.Column('actual_status_code', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_check_executions_id'), 'check_executions', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_check_executions_id'), table_name='check_executions')
    op.drop_table('check_executions')
    op.drop_index(op.f('ix_checks_id'), table_name='checks')
    op.drop_table('checks')
