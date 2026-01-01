"""add error column and unique check name

Revision ID: 5b3c2f1d4a90
Revises: 84db4cb422c3
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5b3c2f1d4a90"
down_revision: Union[str, Sequence[str], None] = "84db4cb422c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add error column and enforce unique check names; create tables if missing."""
    conn = op.get_bind()

    # Ensure base tables exist (handles older bad migration that dropped them)
    conn.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS checks (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            url VARCHAR NOT NULL,
            required_fields JSON NOT NULL,
            expected_status_code INTEGER DEFAULT 200,
            latency_threshold_ms INTEGER,
            interval_minutes INTEGER DEFAULT 5,
            created_at TIMESTAMP
        );
        """
    ))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_checks_id ON checks (id);"))

    conn.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS check_executions (
            id SERIAL PRIMARY KEY,
            check_id INTEGER NOT NULL REFERENCES checks(id),
            status VARCHAR NOT NULL,
            missing_fields JSON,
            actual_status_code INTEGER,
            latency_ms INTEGER,
            error TEXT,
            executed_at TIMESTAMP
        );
        """
    ))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_check_executions_id ON check_executions (id);"))

    # Add error column if missing
    error_col_exists = conn.execute(sa.text(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'check_executions' AND column_name = 'error'
        """
    )).scalar()
    if not error_col_exists:
        op.add_column("check_executions", sa.Column("error", sa.Text(), nullable=True))

    # Enforce unique check name (via unique index if not present)
    unique_exists = conn.execute(sa.text(
        """
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_checks_name'
        UNION ALL
        SELECT 1 FROM pg_indexes WHERE indexname = 'uq_checks_name_idx'
        LIMIT 1
        """
    )).scalar()
    if not unique_exists:
        conn.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_checks_name_idx ON checks (name);"))


def downgrade() -> None:
    """Remove error column and unique constraint."""
    conn = op.get_bind()
    # Drop unique index/constraint if present
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_checks_name_idx;"))
    op.drop_column("check_executions", "error")
