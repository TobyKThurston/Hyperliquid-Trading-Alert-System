"""Alert delivery attempt API models."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeliveryAttemptResponse(BaseModel):
    """A single delivery attempt for an alert."""

    id: UUID
    alert_id: UUID
    attempt_no: int
    status: str
    response_code: Optional[int]
    latency_ms: Optional[int]
    error: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryAttemptListResponse(BaseModel):
    """List of delivery attempts for an alert, newest first."""

    attempts: list[DeliveryAttemptResponse]
    total: int
