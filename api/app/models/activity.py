"""Activity log model for audit trail."""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ActivityLog(Base):
    """
    Activity log for auditing user actions.

    Tracks read, create, update, delete operations on resources
    with HTTP context for compliance and debugging.
    """

    __tablename__ = "activity_log"

    id = Column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    timestamp = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    api_key_id = Column(PG_UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="SET NULL"))
    action = Column(
        Enum("read", "create", "update", "delete", name="activity_action"),
        nullable=False,
    )
    resource = Column(
        Enum(
            "article",
            "bulletin_post",
            "bulletin_comment",
            "profile",
            "user",
            "api_key",
            name="resource_type",
        ),
        nullable=False,
    )
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False)
    request_id = Column(Text)
    ip_address = Column(INET)
    user_agent = Column(String(512))
    extra_data = Column(JSONB, server_default=text("'{}'::jsonb"))  # Called 'metadata' in design, but that's reserved in SQLAlchemy

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_activity_resource", "resource", "resource_id", "timestamp"),
        Index("idx_activity_user", "user_id", "timestamp"),
        Index("idx_activity_timestamp", "timestamp"),
    )
