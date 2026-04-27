"""Alert API models."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal


class AlertResponse(BaseModel):
    """Response model for an alert."""

    id: UUID
    rule_id: UUID
    symbol: str
    rule_type: str
    triggered_at: datetime
    trigger_value: Optional[Decimal]
    delivery_status: str
    delivery_attempts: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    """Response model for listing alerts."""

    alerts: list[AlertResponse]
    total: int

