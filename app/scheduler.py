import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.models import Check, APICheck
from app.crud import get_checks, create_execution
from app.checker import run_check

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 30},
    timezone="UTC",
)

def _job_id(check_id: int) -> str:
    return f"check_{check_id}"

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
    if scheduler.running:
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
