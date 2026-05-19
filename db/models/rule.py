"""Rule database model."""

import uuid
from typing import Literal

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.time import utcnow
from db.base import Base

RuleType = Literal[
    "price_threshold",
    "percent_move",
    "candle_close",
    "macd_cross",
    "rsi",
    "bollinger_bands",
]


class Rule(Base):
    """Alert rule model."""

    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    rule_type = Column(
        SQLEnum(
            "price_threshold",
            "percent_move",
            "candle_close",
            "macd_cross",
            "rsi",
            "bollinger_bands",
            name="rule_type_enum",
        ),
        nullable=False,
    )
    symbol = Column(String, nullable=False)
    # JSONB on Postgres, generic JSON on other backends (e.g. SQLite in tests).
    config = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    cooldown_seconds = Column(Integer, default=0)
    discord_webhook_url = Column(String, nullable=True)
    generic_webhook_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")
