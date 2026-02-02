"""Profile model for user bio content."""

from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Profile(Base):
    """
    User profile content.

    Stores the user's markdown bio separately from the users table.
    """

    __tablename__ = "profiles"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content_md = Column(Text, nullable=False, server_default=text("''"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    user = relationship("User", back_populates="profile")
