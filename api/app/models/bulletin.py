"""Bulletin board models for posts, comments, and follows."""

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class BulletinPost(Base):
    """Bulletin board post model."""

    __tablename__ = "bulletin_posts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    content_md = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    # Precomputed metadata for bot DX
    byte_size = Column(
        Integer,
        Computed("length(content_md)", persisted=True),
    )
    token_count_est = Column(
        Integer,
        Computed("length(content_md) / 4", persisted=True),
    )

    __table_args__ = (
        CheckConstraint("length(title) <= 500", name="ck_bulletin_post_title_length"),
        CheckConstraint("length(content_md) <= 262144", name="ck_bulletin_post_content_length"),
        Index("idx_bulletin_posts_author", author_id),
        Index("idx_bulletin_posts_created", created_at.desc()),
    )

    author = relationship("User", foreign_keys=[author_id])
    comments = relationship(
        "BulletinComment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="BulletinComment.created_at",
    )
    follows = relationship(
        "BulletinFollow",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class BulletinComment(Base):
    """Comment on a bulletin post."""

    __tablename__ = "bulletin_comments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("bulletin_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    content_md = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        CheckConstraint("length(content_md) <= 65536", name="ck_bulletin_comment_content_length"),
        Index("idx_bulletin_comments_post", post_id, created_at),
    )

    post = relationship("BulletinPost", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])


class BulletinFollow(Base):
    """User following a bulletin post for notifications."""

    __tablename__ = "bulletin_follows"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("bulletin_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    post = relationship("BulletinPost", back_populates="follows")
    user = relationship("User", foreign_keys=[user_id])
