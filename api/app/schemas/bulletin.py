"""Bulletin-related Pydantic schemas."""

from pydantic import BaseModel, field_validator


class CreatePostRequest(BaseModel):
    """Request to create a new bulletin post."""

    title: str
    content_md: str

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
        if len(v) > 262144:  # 256KB
            raise ValueError("Content must be 256KB or less")
        return v


class UpdatePostRequest(BaseModel):
    """Request to update a bulletin post."""

    title: str | None = None
    content_md: str | None = None

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
        if v is not None and len(v) > 262144:
            raise ValueError("Content must be 256KB or less")
        return v


class CommentRequest(BaseModel):
    """Request to add a comment."""

    content_md: str

    @field_validator("content_md")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content length."""
        if len(v) > 65536:  # 64KB
            raise ValueError("Comment must be 64KB or less")
        if not v.strip():
            raise ValueError("Comment cannot be empty")
        return v


class CommentResponse(BaseModel):
    """Response for a comment."""

    id: str
    post_id: str
    author: str | None
    author_id: str | None
    content_md: str
    created_at: str


class PostListItem(BaseModel):
    """Post summary for list endpoints."""

    id: str
    title: str
    author: str | None
    author_id: str | None
    created_at: str
    updated_at: str
    comment_count: int
    byte_size: int
    token_count_est: int


class PostResponse(BaseModel):
    """Full post response without comments."""

    id: str
    title: str
    content_md: str
    author: str | None
    author_id: str | None
    created_at: str
    updated_at: str
    byte_size: int
    token_count_est: int


class PostWithCommentsResponse(BaseModel):
    """Full post response with comments."""

    id: str
    title: str
    content_md: str
    author: str | None
    author_id: str | None
    created_at: str
    updated_at: str
    byte_size: int
    token_count_est: int
    comments: list[CommentResponse]


class ListPostsResponse(BaseModel):
    """Response for listing posts."""

    items: list[PostListItem]
    next_cursor: str | None
    has_more: bool


class FollowResponse(BaseModel):
    """Response for follow action."""

    post_id: str
    following: bool
