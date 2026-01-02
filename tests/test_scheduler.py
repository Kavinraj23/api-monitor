import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore


def test_schedule_check_job_registers_job():
    # Use in-memory DB and scheduler job store to avoid external services
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("SCHEDULER_ENABLED", "true")

    from app import scheduler as sched

    # Swap to a memory job store so adding jobs does not hit the database
    sched.scheduler = BackgroundScheduler(jobstores={"default": MemoryJobStore()}, timezone="UTC")
    sched.scheduler.remove_all_jobs()
    sched.scheduler.start()

    try:
        dummy_check = type("Check", (), {"id": 123, "name": "demo", "interval_minutes": 1})

        sched.schedule_check_job(dummy_check)

        jobs = sched.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == sched._job_id(dummy_check.id)
    finally:
        sched.scheduler.shutdown(wait=False)
