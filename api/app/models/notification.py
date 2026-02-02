"""Notification model for the inbox system."""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Notification(Base):
    """User notification model."""

    __tablename__ = "notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_type = Column(String, nullable=False)  # e.g., "comment", "follow", "mention"
    title = Column(Text, nullable=False)
    body = Column(Text)
    resource_type = Column(String)  # e.g., "article", "bulletin_post", "bulletin_comment"
    resource_id = Column(PG_UUID(as_uuid=True))
    payload = Column(JSONB, server_default=text("'{}'::jsonb"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    read_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("idx_notifications_user", user_id, created_at.desc()),
        Index(
            "idx_notifications_unread",
            user_id,
            created_at.desc(),
            postgresql_where=(read_at.is_(None)),
        ),
    )

    user = relationship("User", foreign_keys=[user_id])
