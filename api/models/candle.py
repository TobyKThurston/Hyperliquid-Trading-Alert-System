"""Candle API models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CandleResponse(BaseModel):
    """Response model for a candle."""

    id: UUID
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    interval_seconds: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandleListResponse(BaseModel):
    """Response model for listing candles."""

    candles: list[CandleResponse]
    total: int
    limit: int
    offset: int
    order: str
