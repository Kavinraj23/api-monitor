from typing import List

from sqlalchemy.orm import Session

from app.models import Check, CheckExecution

# ============ CHECK OPERATIONS ============

def create_check(
    db: Session,
    name: str,
    url: str,
    required_fields: List[str],
    expected_status_code: int = 200,
    latency_threshold_ms: int | None = None,
    interval_minutes: int = 5,
) -> Check:
    """Create a new API check"""
    db_check = Check(
        name=name,
        url=str(url),  # Convert HttpUrl to string
        required_fields=required_fields,
        expected_status_code=expected_status_code,
        latency_threshold_ms=latency_threshold_ms,
        interval_minutes=interval_minutes,
    )
    try:
        db.add(db_check)
        db.commit()
        db.refresh(db_check)
        return db_check
    except Exception:
        db.rollback()
        raise

def get_check(db: Session, check_id: int) -> Optional[Check]:
    """Get a check by ID"""
    return db.query(Check).filter(Check.id == check_id).first()

def get_checks(db: Session, skip: int = 0, limit: int = 100) -> List[Check]:
    """Get all checks with pagination"""
    return db.query(Check).offset(skip).limit(limit).all()

def delete_check(db: Session, check_id: int) -> bool:
    """Delete a check"""
    db_check = db.query(Check).filter(Check.id == check_id).first()
    if db_check:
        db.delete(db_check)
        db.commit()
        return True
    return False

# ============ EXECUTION OPERATIONS ============
# after run_check, we record the result here
def create_execution(
    db: Session,
    check_id: int,
    status: str,
    missing_fields: List[str],
    actual_status_code: int = None,
    latency_ms: float = None,
    error: Optional[str] = None,
) -> CheckExecution:
    """Record a check execution result"""
    db_execution = CheckExecution(
        check_id=check_id,
        status=status,
        missing_fields=missing_fields,
        actual_status_code=actual_status_code,
        latency_ms=latency_ms,
        error=error,
    )
    try:
        db.add(db_execution)
        db.commit()
        db.refresh(db_execution)
        return db_execution
    except Exception:
        db.rollback()
        raise

def get_check_history(
    db: Session,
    check_id: int,
    limit: int = 50
) -> List[CheckExecution]:
    """Get execution history for a check"""
    return (
        db.query(CheckExecution)
        .filter(CheckExecution.check_id == check_id)
        .order_by(CheckExecution.executed_at.desc())
        .limit(limit)
        .all()
    )

def get_latest_execution(db: Session, check_id: int) -> Optional[CheckExecution]:
    """Get the most recent execution for a check"""
    return (
        db.query(CheckExecution)
        .filter(CheckExecution.check_id == check_id)
        .order_by(CheckExecution.executed_at.desc())
        .first()
    )