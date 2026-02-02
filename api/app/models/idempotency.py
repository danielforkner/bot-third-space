"""Idempotency key model for safe write operation retries."""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app.database import Base


class IdempotencyKey(Base):
    """
    Idempotency key tracking for write operations.

    Scoped by (key, user_id) to prevent cross-user collisions.
    Stores response for replay on duplicate requests.
    """

    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    method = Column(String(10), nullable=False)
    path = Column(Text, nullable=False)
    request_hash = Column(String(64), nullable=False)  # SHA256 of request body
    status = Column(
        Enum("processing", "completed", "failed", name="idempotency_status"),
        nullable=False,
        server_default=text("'processing'"),
    )
    response_body = Column(JSONB)
    response_status = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    completed_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("idx_idempotency_created", "created_at"),
    )
