"""Bulletin router for posts, comments, and follows."""

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user, get_effective_scopes
from app.database import get_db
from app.models.bulletin import BulletinComment, BulletinFollow, BulletinPost
from app.models.user import APIKey, User
from app.schemas.bulletin import (
    CommentRequest,
    CommentResponse,
    CreatePostRequest,
    FollowResponse,
    ListPostsResponse,
    PostListItem,
    PostResponse,
    PostWithCommentsResponse,
    UpdatePostRequest,
)

router = APIRouter(prefix="/api/v1/bulletin", tags=["Bulletin"])


def require_scope(required_scope: str):
    """Dependency factory to require a specific scope."""

    async def check_scope(
        auth: tuple[User, APIKey] = Depends(get_current_user),
    ) -> tuple[User, APIKey]:
        user, api_key = auth
        scopes = get_effective_scopes(user, api_key)

        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Scope '{required_scope}' required",
                    }
                },
            )

        return user, api_key

    return check_scope


def _get_author_display(user: User | None) -> str | None:
    """Get display name for author."""
    if not user:
        return None
    return user.display_name or user.username


# --- List Posts ---


@router.get(
    "/posts",
    response_model=ListPostsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_posts(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:read")),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ListPostsResponse:
    """
    List bulletin posts with cursor-based pagination.

    Returns posts ordered by created_at descending.
    """
    # Subquery for comment counts
    comment_count_subq = (
        select(
            BulletinComment.post_id,
            func.count(BulletinComment.id).label("comment_count"),
        )
        .group_by(BulletinComment.post_id)
        .subquery()
    )

    query = (
        select(BulletinPost, func.coalesce(comment_count_subq.c.comment_count, 0).label("comment_count"))
        .outerjoin(comment_count_subq, BulletinPost.id == comment_count_subq.c.post_id)
        .options(selectinload(BulletinPost.author))
    )

    # Apply cursor (cursor is the created_at timestamp)
    if cursor:
        try:
            cursor_dt = dt.datetime.fromisoformat(cursor)
            query = query.where(BulletinPost.created_at < cursor_dt)
        except ValueError:
            pass  # Invalid cursor, ignore

    query = query.order_by(BulletinPost.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    rows = list(result.all())

    # Check if there are more items
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    items = [
        PostListItem(
            id=str(post.id),
            title=post.title,
            author=_get_author_display(post.author),
            author_id=str(post.author_id) if post.author_id else None,
            created_at=post.created_at.isoformat(),
            updated_at=post.updated_at.isoformat(),
            comment_count=comment_count,
            byte_size=post.byte_size or 0,
            token_count_est=post.token_count_est or 0,
        )
        for post, comment_count in rows
    ]

    next_cursor = rows[-1][0].created_at.isoformat() if rows and has_more else None

    return ListPostsResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# --- Create Post ---


@router.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    data: CreatePostRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> PostResponse:
    """Create a new bulletin post."""
    user, _ = auth

    post = BulletinPost(
        title=data.title,
        content_md=data.content_md,
        author_id=user.id,
    )

    db.add(post)
    await db.commit()

    # Re-fetch to get computed columns
    result = await db.execute(
        select(BulletinPost).options(selectinload(BulletinPost.author)).where(BulletinPost.id == post.id)
    )
    post = result.scalar_one()

    return PostResponse(
        id=str(post.id),
        title=post.title,
        content_md=post.content_md,
        author=_get_author_display(post.author),
        author_id=str(post.author_id) if post.author_id else None,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        byte_size=post.byte_size or 0,
        token_count_est=post.token_count_est or 0,
    )


# --- Get Post ---


@router.get(
    "/posts/{post_id}",
    response_model=PostWithCommentsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:read")),
) -> PostWithCommentsResponse:
    """Get a single post by ID with comments."""
    result = await db.execute(
        select(BulletinPost)
        .options(
            selectinload(BulletinPost.author),
            selectinload(BulletinPost.comments).selectinload(BulletinComment.author),
        )
        .where(BulletinPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    comments = [
        CommentResponse(
            id=str(comment.id),
            post_id=str(comment.post_id),
            author=_get_author_display(comment.author),
            author_id=str(comment.author_id) if comment.author_id else None,
            content_md=comment.content_md,
            created_at=comment.created_at.isoformat(),
        )
        for comment in post.comments
    ]

    return PostWithCommentsResponse(
        id=str(post.id),
        title=post.title,
        content_md=post.content_md,
        author=_get_author_display(post.author),
        author_id=str(post.author_id) if post.author_id else None,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        byte_size=post.byte_size or 0,
        token_count_est=post.token_count_est or 0,
        comments=comments,
    )


# --- Update Post ---


@router.patch(
    "/posts/{post_id}",
    response_model=PostResponse,
    status_code=status.HTTP_200_OK,
)
async def update_post(
    post_id: UUID,
    data: UpdatePostRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> PostResponse:
    """
    Update a bulletin post.

    Only the post author can update their post.
    """
    user, _ = auth

    result = await db.execute(
        select(BulletinPost).options(selectinload(BulletinPost.author)).where(BulletinPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    # Check ownership
    if post.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You can only update your own posts",
                }
            },
        )

    # Update fields
    if data.title is not None:
        post.title = data.title
    if data.content_md is not None:
        post.content_md = data.content_md

    post.updated_at = dt.datetime.now(dt.UTC)

    await db.commit()

    # Re-fetch to get computed columns
    result = await db.execute(
        select(BulletinPost).options(selectinload(BulletinPost.author)).where(BulletinPost.id == post.id)
    )
    post = result.scalar_one()

    return PostResponse(
        id=str(post.id),
        title=post.title,
        content_md=post.content_md,
        author=_get_author_display(post.author),
        author_id=str(post.author_id) if post.author_id else None,
        created_at=post.created_at.isoformat(),
        updated_at=post.updated_at.isoformat(),
        byte_size=post.byte_size or 0,
        token_count_est=post.token_count_est or 0,
    )


# --- Delete Post ---


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> None:
    """
    Delete a bulletin post.

    Only the post author can delete their post.
    """
    user, _ = auth

    result = await db.execute(select(BulletinPost).where(BulletinPost.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    # Check ownership
    if post.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "You can only delete your own posts",
                }
            },
        )

    await db.delete(post)
    await db.commit()


# --- Add Comment ---


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: UUID,
    data: CommentRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> CommentResponse:
    """Add a comment to a post."""
    user, _ = auth

    # Check post exists
    result = await db.execute(select(BulletinPost).where(BulletinPost.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    comment = BulletinComment(
        post_id=post_id,
        author_id=user.id,
        content_md=data.content_md,
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return CommentResponse(
        id=str(comment.id),
        post_id=str(comment.post_id),
        author=user.display_name or user.username,
        author_id=str(user.id),
        content_md=comment.content_md,
        created_at=comment.created_at.isoformat(),
    )


# --- Follow Post ---


@router.post(
    "/posts/{post_id}/follow",
    response_model=FollowResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> FollowResponse:
    """Follow a post for notifications."""
    user, _ = auth

    # Check post exists
    result = await db.execute(select(BulletinPost).where(BulletinPost.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    # Check if already following
    result = await db.execute(
        select(BulletinFollow).where(
            BulletinFollow.user_id == user.id,
            BulletinFollow.post_id == post_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Already following, return success (idempotent)
        return FollowResponse(post_id=str(post_id), following=True)

    follow = BulletinFollow(
        user_id=user.id,
        post_id=post_id,
    )

    db.add(follow)
    await db.commit()

    return FollowResponse(post_id=str(post_id), following=True)


# --- Unfollow Post ---


@router.delete(
    "/posts/{post_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unfollow_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("bulletin:write")),
) -> None:
    """Unfollow a post."""
    user, _ = auth

    # Check post exists
    result = await db.execute(select(BulletinPost).where(BulletinPost.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Post '{post_id}' not found",
                }
            },
        )

    # Find follow
    result = await db.execute(
        select(BulletinFollow).where(
            BulletinFollow.user_id == user.id,
            BulletinFollow.post_id == post_id,
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "You are not following this post",
                }
            },
        )

    await db.delete(follow)
    await db.commit()
