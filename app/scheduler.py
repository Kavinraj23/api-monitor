import asyncio
import logging
import os
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal, engine
from app.models import Check, APICheck
from app.crud import get_checks, create_execution
from app.checker import run_check

logger = logging.getLogger(__name__)

SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
ADVISORY_LOCK_ID = int(os.getenv("SCHEDULER_ADVISORY_LOCK_ID", "672311"))

jobstores = {
    "default": SQLAlchemyJobStore(url=os.getenv("DATABASE_URL")),
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 30},
    timezone="UTC",
)

_scheduler_lock_conn = None

def _job_id(check_id: int) -> str:
    return f"check_{check_id}"


def _is_postgres() -> bool:
    url = os.getenv("DATABASE_URL", "")
    return url.startswith("postgres") or url.startswith("postgresql")


def acquire_scheduler_lock() -> bool:
    """Try to acquire a Postgres advisory lock so only one scheduler instance runs."""
    global _scheduler_lock_conn
    if not _is_postgres():
        return True
    conn = engine.raw_connection()
    cur = conn.cursor()
    cur.execute("SELECT pg_try_advisory_lock(%s);", (ADVISORY_LOCK_ID,))
    locked = cur.fetchone()[0]
    if not locked:
        conn.close()
        return False
    _scheduler_lock_conn = conn
    return True


def release_scheduler_lock():
    global _scheduler_lock_conn
    if _scheduler_lock_conn is None:
        return
    try:
        cur = _scheduler_lock_conn.cursor()
        cur.execute("SELECT pg_advisory_unlock(%s);", (ADVISORY_LOCK_ID,))
    finally:
        _scheduler_lock_conn.close()
        _scheduler_lock_conn = None

async def run_check_task(check_id: int):
    """Background task to run a check and save execution result"""
    db = SessionLocal()
    try:
        from app.crud import get_check
        db_check = get_check(db, check_id)
        if not db_check:
            logger.warning(f"Check {check_id} not found")
            return

        # Build APICheck payload
        payload = APICheck(
            method="GET",
            url=db_check.url,
            required_fields=db_check.required_fields,
            expected_status_code=db_check.expected_status_code,
            latency_threshold_ms=db_check.latency_threshold_ms,
        )

        # Run the check
        result = await run_check(payload)

        # Save execution result
        create_execution(
            db=db,
            check_id=db_check.id,
            status=result.get("status", "FAIL"),
            missing_fields=result.get("missing_fields", []),
            actual_status_code=result.get("status_code"),
            latency_ms=result.get("latency_ms"),
            error=result.get("error"),
        )
        logger.info(f"Check {check_id} ({db_check.name}) executed: {result.get('status')}")
    except Exception as e:
        logger.error(f"Error running check {check_id}: {e}")
    finally:
        db.close()

def run_check_task_sync(check_id: int):
    """Wrapper to run async check task in sync context"""
    asyncio.run(run_check_task(check_id))

def schedule_check_job(check: Check):
    try:
        scheduler.add_job(
            run_check_task_sync,
            'interval',
            minutes=check.interval_minutes,
            args=[check.id],
            id=_job_id(check.id),
            replace_existing=True,
        )
        logger.info(f"Scheduled check {check.id} ({check.name}) to run every {check.interval_minutes} minutes")
    except Exception as e:
        logger.error(f"Error scheduling check {check.id} ({check.name}): {e}")

def start_scheduler():
    """Start the scheduler and load all checks"""
    if not SCHEDULER_ENABLED:
        logger.info("Scheduler disabled via SCHEDULER_ENABLED=false")
        return
    if scheduler.running:
        return
    if not acquire_scheduler_lock():
        logger.warning("Scheduler lock not acquired; another instance is running")
        return
    scheduler.start()
    db = SessionLocal()
    try:
        checks = get_checks(db)
        for check in checks:
            schedule_check_job(check)
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
    finally:
        db.close()


def stop_scheduler():
    """Stop the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    release_scheduler_lock()


def is_scheduler_running() -> bool:
    """Expose scheduler running state for health checks"""
    return scheduler.running


def scheduler_health() -> dict:
    """Return scheduler health details including job store reachability and job count."""
    running = scheduler.running
    try:
        jobs = scheduler.get_jobs()
        job_count = len(jobs)
        jobstore_ok = True
    except Exception:
        logger.exception("Scheduler jobstore check failed")
        job_count = None
        jobstore_ok = False
    return {
        "running": running,
        "jobstore_ok": jobstore_ok,
        "job_count": job_count,
        "scheduler_enabled": SCHEDULER_ENABLED,
        "lock_held": _scheduler_lock_conn is not None,
    }
