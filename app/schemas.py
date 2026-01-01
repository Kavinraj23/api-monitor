from pydantic import BaseModel, HttpUrl, validator
from typing import List, Optional
from datetime import datetime

class CheckCreate(BaseModel):
    name: str
    url: HttpUrl
    required_fields: List[str]
    expected_status_code: int = 200
    latency_threshold_ms: Optional[int] = None
    interval_minutes: int = 5  # ADD THIS

    @validator("interval_minutes")
    def interval_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("interval_minutes must be greater than 0")
        return value

    @validator("latency_threshold_ms")
    def latency_non_negative(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("latency_threshold_ms must be non-negative")
        return value

    @validator("required_fields")
    def required_fields_non_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("required_fields must contain at least one field")
        if any((not f) or (not f.strip()) for f in value):
            raise ValueError("required_fields entries must be non-empty strings")
        return value

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
    error: Optional[str]
    executed_at: datetime

    class Config:
        from_attributes = True