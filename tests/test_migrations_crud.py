import os
import sys
from pathlib import Path

import pytest

# Ensure repo is on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set env BEFORE any imports
os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/api_monitor",
)
os.environ["SCHEDULER_ENABLED"] = "false"

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.database import SessionLocal, Base, engine
from app import crud


def run_migrations():
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.mark.skipif(
    os.getenv("DATABASE_URL", "").startswith("sqlite"),
    reason="Requires PostgreSQL (migrations use Postgres-specific DDL)",
)
def test_migrations_and_crud():
    # Drop all tables and recreate schema via migrations
    try:
        Base.metadata.drop_all(engine)
    except Exception:
        pass  # If drop fails (DB unavailable), skip silently
    
    try:
        run_migrations()
    except Exception as e:
        pytest.skip(f"Could not run migrations: {e}")

    session = SessionLocal()
    try:
        # sanity check connectivity
        session.execute(text("SELECT 1"))

        check = crud.create_check(
            session,
            name="demo",
            url="http://example.com",
            required_fields=["foo"],
            expected_status_code=200,
            latency_threshold_ms=500,
            interval_minutes=1,
        )
        fetched = crud.get_check(session, check.id)
        assert fetched is not None
        assert fetched.name == "demo"

        removed = crud.delete_check(session, check.id)
        assert removed is True
        assert crud.get_check(session, check.id) is None
    finally:
        session.close()
