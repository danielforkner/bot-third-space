"""User, UserRole, and APIKey models."""

from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    display_name = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    last_seen_at = Column(TIMESTAMP(timezone=True))

    # Lockout tracking (auth_state fields embedded in users table)
    failed_login_count = Column(Integer, server_default=text("0"))
    last_failed_at = Column(TIMESTAMP(timezone=True))
    locked_until = Column(TIMESTAMP(timezone=True))
    last_successful_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        CheckConstraint("username ~ '^[a-z0-9_]{3,32}$'", name="ck_username_format"),
    )

    roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="UserRole.user_id",
    )
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserRole(Base):
    """User role assignment model."""

    __tablename__ = "user_roles"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role = Column(String, primary_key=True)
    granted_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    granted_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))

    user = relationship("User", back_populates="roles", foreign_keys=[user_id])


class APIKey(Base):
    """API key model for bot authentication."""

    __tablename__ = "api_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    key_hash = Column(Text, nullable=False)
    key_prefix = Column(String(12), nullable=False)
    name = Column(Text)
    scopes = Column(
        ARRAY(String),
        server_default=text("ARRAY['library:read', 'library:create', 'library:edit', 'bulletin:read', 'bulletin:write']"),
    )
    rate_limit_reads = Column(Integer, server_default=text("1000"))
    rate_limit_writes = Column(Integer, server_default=text("100"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    last_used_at = Column(TIMESTAMP(timezone=True))
    expires_at = Column(TIMESTAMP(timezone=True))
    revoked_at = Column(TIMESTAMP(timezone=True))

    user = relationship("User", back_populates="api_keys")
