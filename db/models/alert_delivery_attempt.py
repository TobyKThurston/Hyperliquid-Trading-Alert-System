"""Alert delivery attempt database model."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base import Base
import uuid

from core.time import utcnow


class AlertDeliveryAttempt(Base):
    """Model for tracking individual alert delivery attempts."""

    __tablename__ = "alert_delivery_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    attempt_no = Column(Integer, nullable=False)  # 1-indexed attempt number
    status = Column(String, nullable=False)  # "success" or "failed"
    response_code = Column(Integer, nullable=True)  # HTTP status code
    latency_ms = Column(Integer, nullable=True)  # Latency in milliseconds
    error = Column(Text, nullable=True)  # Error message if failed
    created_at = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="delivery_attempt_records")

