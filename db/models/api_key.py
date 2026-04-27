"""API key database model.

Keys are stored as SHA-256 hashes — the raw key is shown to the admin
exactly once at creation time, then discarded. The hash-based lookup means
a leaked DB dump cannot be replayed directly against the API.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from core.time import utcnow
from db.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # Human label ("prod-dashboard", "alex-cli")
    key_hash = Column(String, nullable=False, unique=True, index=True)
    requests_per_minute = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
