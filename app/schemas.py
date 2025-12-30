from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class CheckCreate(BaseModel):
    name: str
    url: HttpUrl
    required_fields: List[str]
    expected_status_code: int = 200
    latency_threshold_ms: Optional[int] = None
    interval_minutes: int = 5  # ADD THIS

class CheckResponse(BaseModel):
    id: int
    name: str
    url: HttpUrl
    required_fields: List[str]
    expected_status_code: int
    latency_threshold_ms: Optional[int]
    interval_minutes: int  # ADD THIS

    # allows fastapi to convert from sqlalchemy model to pydantic model
    class Config:
        from_attributes = True  
        
class CheckExecutionResponse(BaseModel):
    id: int
    check_id: int
    status: str
    missing_fields: List[str]
    actual_status_code: Optional[int]
    latency_ms: Optional[float]
    executed_at: datetime

    class Config:
        from_attributes = True