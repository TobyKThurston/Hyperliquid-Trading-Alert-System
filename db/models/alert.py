"""Alert database model."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from core.time import utcnow
from db.base import Base


class AlertDeliveryStatus:
    """Alert delivery status constants."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class Alert(Base):
    """Alert model for triggered rules."""

    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id"), nullable=False)
    symbol = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)
    triggered_at = Column(DateTime, nullable=False)
    trigger_value = Column(Numeric(precision=20, scale=8), nullable=True)
    window_start = Column(DateTime, nullable=False)  # For idempotency
    window_end = Column(DateTime, nullable=False)
    delivery_status = Column(
        SQLEnum("pending", "delivered", "failed", name="delivery_status_enum"),
        default=AlertDeliveryStatus.PENDING,
        nullable=False,
    )
    delivery_attempts = Column(Integer, default=0, nullable=False)
    last_delivery_attempt = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Unique constraint for idempotency
    __table_args__ = (
        UniqueConstraint("rule_id", "window_start", "window_end", name="uq_alert_window"),
    )

    # Relationships
    rule = relationship("Rule", back_populates="alerts")
    delivery_attempt_records = relationship(
        "AlertDeliveryAttempt", back_populates="alert", cascade="all, delete-orphan"
    )
