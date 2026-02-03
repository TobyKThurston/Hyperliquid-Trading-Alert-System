"""Rule database model."""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db.base import Base
import uuid
from datetime import datetime
from typing import Literal


RuleType = Literal["price_threshold", "percent_move", "candle_close", "macd_cross"]


class Rule(Base):
    """Alert rule model."""

    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    rule_type = Column(
        SQLEnum("price_threshold", "percent_move", "candle_close", "macd_cross", name="rule_type_enum"),
        nullable=False,
    )
    symbol = Column(String, nullable=False)
    config = Column(JSONB, nullable=False)  # Rule-specific parameters
    cooldown_seconds = Column(Integer, default=0)
    discord_webhook_url = Column(String, nullable=True)
    generic_webhook_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    alerts = relationship("Alert", back_populates="rule", cascade="all, delete-orphan")

