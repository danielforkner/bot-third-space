"""Library-related Pydantic schemas."""

import re

from pydantic import BaseModel, field_validator


class CreateArticleRequest(BaseModel):
    """Request to create a new article."""

    title: str
    content_md: str
    slug: str | None = None  # Auto-generated if not provided

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title length."""
        if len(v) > 500:
            raise ValueError("Title must be 500 characters or less")
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("content_md")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content length."""
        if len(v) > 1048576:  # 1MB
            raise ValueError("Content must be 1MB or less")
        return v

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        """Validate slug format."""
        if v is not None and not re.match(r"^[a-z0-9-]{3,128}$", v):
            raise ValueError(
                "Slug must be 3-128 characters, lowercase letters, numbers, and hyphens only"
            )
        return v


class UpdateArticleRequest(BaseModel):
    """Request to update an article."""

    title: str | None = None
    content_md: str | None = None
    edit_summary: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate title length."""
        if v is not None:
            if len(v) > 500:
                raise ValueError("Title must be 500 characters or less")
            if not v.strip():
                raise ValueError("Title cannot be empty")
        return v

    @field_validator("content_md")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        """Validate content length."""
        if v is not None and len(v) > 1048576:
            raise ValueError("Content must be 1MB or less")
        return v


class ArticleListItem(BaseModel):
    """Article summary for list endpoints."""

    slug: str
    title: str
    author: str | None
    author_id: str | None
    created_at: str
    updated_at: str
    current_version: int
    byte_size: int
    token_count_est: int


class ArticleResponse(BaseModel):
    """Full article response."""

    id: str
    slug: str
    title: str
    content_md: str
    author: str | None
    author_id: str | None
    created_at: str
    updated_at: str
    current_version: int
    byte_size: int
    token_count_est: int


class ListArticlesResponse(BaseModel):
    """Response for listing articles."""

    items: list[ArticleListItem]
    next_cursor: str | None
    has_more: bool


class SearchResultItem(BaseModel):
    """Search result item with snippet."""

    slug: str
    title: str
    snippet: str | None = None
    rank: float | None = None
    byte_size: int
    token_count_est: int


class SearchResponse(BaseModel):
    """Search results response."""

    items: list[SearchResultItem]
    total_count: int


class BatchReadRequest(BaseModel):
    """Request to batch read articles."""

    slugs: list[str]

    @field_validator("slugs")
    @classmethod
    def validate_slugs(cls, v: list[str]) -> list[str]:
        """Validate batch size."""
        if len(v) > 100:
            raise ValueError("Maximum 100 articles per batch request")
        return v


class BatchReadResponse(BaseModel):
    """Response for batch read."""

    items: list[ArticleResponse]
    missing: list[str]  # Slugs that were not found


class RevisionListItem(BaseModel):
    """Revision summary for list endpoint."""

    version: int
    title: str
    editor: str | None
    editor_id: str | None
    edit_summary: str | None
    created_at: str
    byte_size: int


class RevisionResponse(BaseModel):
    """Full revision response with content."""

    id: str
    article_id: str
    version: int
    title: str
    content_md: str
    editor: str | None
    editor_id: str | None
    edit_summary: str | None
    created_at: str


class ListRevisionsResponse(BaseModel):
    """Response for listing article revisions."""

    items: list[RevisionListItem]
    article_slug: str
    current_version: int
