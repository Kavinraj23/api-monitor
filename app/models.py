from sqlalchemy import Column, Integer, DateTime, JSON, String, ForeignKey
from pydantic import BaseModel, HttpUrl
from typing import List, Literal, Optional
from datetime import datetime
from app.database import Base

# represents what must be true for the api to be considered "healthy"
class APICheck(BaseModel):
    method: Literal["GET"] # only GET is supported (for now)
    url: HttpUrl
    required_fields: List[str]
    expected_status_code: int = 200
    latency_threshold_ms: Optional[int] = None

class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    required_fields = Column(JSON, nullable=False)
    expected_status_code = Column(Integer, default=200)
    latency_threshold_ms = Column(Integer, default=1000)
    interval_minutes = Column(Integer, default=5)  # Run every 5 minutes by default
    created_at = Column(DateTime, default=datetime.utcnow)

class CheckExecution(Base):
    __tablename__ = "check_executions"

    id = Column(Integer, primary_key=True, index=True)
    check_id = Column(Integer, ForeignKey("checks.id"), nullable=False, index=True)
    status = Column(String, nullable=False)  # "PASS" or "FAIL"
    missing_fields = Column(JSON, nullable=True)
    actual_status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)