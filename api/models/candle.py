"""Candle API models."""
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal


class CandleResponse(BaseModel):
    """Response model for a candle."""

    id: UUID
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal]
    interval_seconds: int
    created_at: datetime

    class Config:
        from_attributes = True


class CandleListResponse(BaseModel):
    """Response model for listing candles."""

    candles: list[CandleResponse]
    total: int
    limit: int
    offset: int
    order: str

