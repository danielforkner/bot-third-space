"""Rate limit bucket model for per-API-key rate limiting."""

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class RateLimitBucket(Base):
    """
    Rate limit bucket for per-API-key rate limiting.

    Tracks request counts per API key within time windows.
    """

    __tablename__ = "rate_limit_buckets"

    api_key_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bucket_type = Column(
        String,
        primary_key=True,
    )
    window_start = Column(
        TIMESTAMP(timezone=True),
        primary_key=True,
    )
    request_count = Column(Integer, server_default=text("0"))

    __table_args__ = (
        CheckConstraint("bucket_type IN ('read', 'write')", name="ck_bucket_type"),
    )

    api_key = relationship("APIKey")
