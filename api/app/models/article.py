"""Article and ArticleRevision models for the Library."""

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Column,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Article(Base):
    """Article model for the Library."""

    __tablename__ = "articles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    slug = Column(String, unique=True, nullable=False)
    title = Column(Text, nullable=False)
    content_md = Column(Text, nullable=False)
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    current_version = Column(Integer, server_default=text("1"))

    # Precomputed metadata for bot DX
    byte_size = Column(
        Integer,
        Computed("length(content_md)", persisted=True),
    )
    token_count_est = Column(
        Integer,
        Computed("length(content_md) / 4", persisted=True),
    )

    # Full-text search vector
    # Note: We'll create the tsvector column via migration since SQLAlchemy
    # has limited support for complex GENERATED ALWAYS expressions
    tsv = Column(TSVECTOR)

    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9-]{3,128}$'", name="ck_article_slug_format"),
        CheckConstraint("length(title) <= 500", name="ck_article_title_length"),
        CheckConstraint("length(content_md) <= 1048576", name="ck_article_content_length"),
        Index("idx_articles_tsv", tsv, postgresql_using="gin"),
        Index("idx_articles_author", author_id),
        Index("idx_articles_slug", slug),
        Index("idx_articles_updated", updated_at.desc()),
    )

    author = relationship("User", foreign_keys=[author_id])
    revisions = relationship(
        "ArticleRevision",
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="ArticleRevision.version.desc()",
    )


class ArticleRevision(Base):
    """Article revision for version history."""

    __tablename__ = "article_revisions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    article_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    title = Column(Text, nullable=False)
    content_md = Column(Text, nullable=False)
    editor_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    edit_summary = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("article_id", "version", name="uq_article_revision_version"),
    )

    article = relationship("Article", back_populates="revisions")
    editor = relationship("User", foreign_keys=[editor_id])
