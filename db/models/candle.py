"""Candle database model for caching market data."""

import uuid

from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint

from core.time import utcnow
from db.base import Base


class Candle(Base):
    """Candle model for storing OHLCV data."""

    __tablename__ = "candles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Numeric(precision=20, scale=8), nullable=False)
    high = Column(Numeric(precision=20, scale=8), nullable=False)
    low = Column(Numeric(precision=20, scale=8), nullable=False)
    close = Column(Numeric(precision=20, scale=8), nullable=False)
    volume = Column(Numeric(precision=20, scale=8), nullable=True)
    interval_seconds = Column(Integer, default=900, nullable=False)  # 15m = 900s
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Unique constraint: one candle per symbol/timestamp/interval
    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", "interval_seconds", name="uq_candle_symbol_time_interval"
        ),
    )
