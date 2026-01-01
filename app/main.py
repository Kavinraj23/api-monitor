import logging
from fastapi import FastAPI, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Check, APICheck
from app.checker import run_check
from app.crud import create_check, get_checks, get_check, get_check_history, create_execution, delete_check
from app.schemas import CheckCreate, CheckResponse, CheckExecutionResponse
from app.database import get_db
from app.scheduler import start_scheduler, stop_scheduler, schedule_check_job, is_scheduler_running, scheduler_health

# configure logging to see scheduler output
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    """Start scheduler on app startup"""
    start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    """Stop scheduler on app shutdown"""
    stop_scheduler()

@app.post("/run-check")
async def run_api_check(check: APICheck, db: Session = Depends(get_db)):
    try:
        result = await run_check(check)
        return result
    except Exception as e:
        logging.exception("Failed to execute ad-hoc check")
        raise HTTPException(status_code=500, detail="Failed to execute check") from e

@app.post("/checks", response_model=CheckResponse, status_code=status.HTTP_201_CREATED)
def create_check_endpoint(check: CheckCreate, db: Session = Depends(get_db)):
    existing = db.query(Check).filter(Check.name == check.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Check with this name already exists")
    db_check = create_check(db, check.name, check.url, check.required_fields, check.expected_status_code, check.latency_threshold_ms, check.interval_minutes)
    try:
        schedule_check_job(db_check)
    except Exception:
        logging.exception(f"Failed to schedule new check {db_check.id}")
    return db_check

@app.get("/checks", response_model=List[CheckResponse])
def list_checks(db: Session = Depends(get_db)):
    return get_checks(db)

@app.get("/checks/{check_id}", response_model=CheckResponse)
def get_check_endpoint(check_id: int, db: Session = Depends(get_db)):
    db_check = get_check(db, check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")
    return db_check

@app.delete("/checks/{check_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_check_endpoint(check_id: int, db: Session = Depends(get_db)):
    """Delete a check by ID"""
    db_check = get_check(db, check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")
    delete_check(db, check_id)
    return None

@app.get("/checks/{check_id}/history", response_model=List[CheckExecutionResponse])
def get_check_history_endpoint(check_id: int, limit: int = 10, db: Session = Depends(get_db)):
    db_check = get_check(db, check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")
    history = get_check_history(db, check_id, limit=limit)
    return history

@app.post("/checks/{check_id}/run", response_model=CheckExecutionResponse)
async def run_check_endpoint(check_id: int, db: Session = Depends(get_db)):
    """Run a check and save the execution result to database"""
    db_check = get_check(db, check_id)
    if not db_check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Build APICheck from stored check
    payload = APICheck(method="GET", url=db_check.url, required_fields=db_check.required_fields, expected_status_code=db_check.expected_status_code, latency_threshold_ms=db_check.latency_threshold_ms)
    # Run the check
    
    try:
        result = await run_check(payload)
    except Exception as e:
        logging.exception(f"Failed to execute check {check_id}")
        raise HTTPException(status_code=500, detail="Failed to execute check") from e

    # Save execution to database
    execution = create_execution(
        db=db,
        check_id=db_check.id,
        status=result.get("status", "FAIL"),
        missing_fields=result.get("missing_fields", []),
        actual_status_code=result.get("status_code"),
        latency_ms=result.get("latency_ms"),
        error=result.get("error"),
    )
    return execution


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Simple health endpoint exposing DB connectivity and scheduler state"""
    scheduler_status = scheduler_health()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        logging.exception("Health check DB failure")
        db_status = "error"
    return {
        "db": db_status,
        "scheduler": scheduler_status,
    }
