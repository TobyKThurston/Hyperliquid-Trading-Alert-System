"""Worker cursor model for persisting ingestion state."""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint
from db.base import Base
import uuid
from datetime import datetime


class WorkerCursor(Base):
    """Worker cursor for tracking last processed timestamp per symbol."""

    __tablename__ = "worker_cursors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    last_processed_timestamp = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Unique constraint: one cursor per worker/symbol
    __table_args__ = (UniqueConstraint("worker_id", "symbol", name="uq_worker_cursor"),)

