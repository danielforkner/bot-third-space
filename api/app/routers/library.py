"""Library router for article CRUD, search, and batch operations."""

import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.article import Article, ArticleRevision
from app.models.user import APIKey, User
from app.schemas.library import (
    ArticleListItem,
    ArticleResponse,
    BatchReadRequest,
    BatchReadResponse,
    CreateArticleRequest,
    ListArticlesResponse,
    SearchResponse,
    SearchResultItem,
    UpdateArticleRequest,
)

router = APIRouter(prefix="/api/v1/library", tags=["Library"])


def require_scope(required_scope: str):
    """Dependency factory to require a specific scope."""

    async def check_scope(
        auth: tuple[User, APIKey] = Depends(get_current_user),
    ) -> tuple[User, APIKey]:
        user, api_key = auth
        scopes = set(api_key.scopes or [])

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


def generate_slug(title: str) -> str:
    """Generate a slug from title with random suffix."""
    # Convert to lowercase, replace spaces and special chars with hyphens
    base = re.sub(r"[^a-z0-9]+", "-", title.lower())
    # Remove leading/trailing hyphens
    base = base.strip("-")
    # Truncate to leave room for suffix
    base = base[:100] if len(base) > 100 else base
    # Add random suffix for uniqueness
    suffix = secrets.token_hex(4)
    return f"{base}-{suffix}"


# --- List Articles ---


@router.get(
    "/articles",
    response_model=ListArticlesResponse,
    status_code=status.HTTP_200_OK,
)
async def list_articles(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ListArticlesResponse:
    """
    List articles with cursor-based pagination.

    Returns articles ordered by updated_at descending.
    """
    query = select(Article).options(selectinload(Article.author))

    # Apply cursor (cursor is the updated_at timestamp)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(Article.updated_at < cursor_dt)
        except ValueError:
            pass  # Invalid cursor, ignore

    query = query.order_by(Article.updated_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    articles = list(result.scalars().all())

    # Check if there are more items
    has_more = len(articles) > limit
    if has_more:
        articles = articles[:limit]

    items = [
        ArticleListItem(
            slug=article.slug,
            title=article.title,
            author=article.author.display_name or article.author.username if article.author else None,
            author_id=str(article.author_id) if article.author_id else None,
            created_at=article.created_at.isoformat(),
            updated_at=article.updated_at.isoformat(),
            current_version=article.current_version,
            byte_size=article.byte_size or 0,
            token_count_est=article.token_count_est or 0,
        )
        for article in articles
    ]

    next_cursor = articles[-1].updated_at.isoformat() if articles and has_more else None

    return ListArticlesResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# --- Create Article ---


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    data: CreateArticleRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("library:create")),
) -> ArticleResponse:
    """
    Create a new article.

    If slug is not provided, one will be auto-generated from the title.
    """
    user, _ = auth

    # Generate slug if not provided
    slug = data.slug or generate_slug(data.title)

    # Validate slug format if provided
    if data.slug and not re.match(r"^[a-z0-9-]{3,128}$", data.slug):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid slug format",
                }
            },
        )

    article = Article(
        slug=slug,
        title=data.title,
        content_md=data.content_md,
        author_id=user.id,
    )

    db.add(article)

    try:
        await db.commit()
        await db.refresh(article)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "Article with this slug already exists",
                }
            },
        )

    # Load author relationship
    await db.refresh(article, ["author"])

    return ArticleResponse(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        content_md=article.content_md,
        author=article.author.display_name or article.author.username if article.author else None,
        author_id=str(article.author_id) if article.author_id else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat(),
        current_version=article.current_version,
        byte_size=article.byte_size or 0,
        token_count_est=article.token_count_est or 0,
    )


# --- Get Article ---


@router.get(
    "/articles/{slug}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> ArticleResponse:
    """Get a single article by slug."""
    result = await db.execute(
        select(Article).options(selectinload(Article.author)).where(Article.slug == slug)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Article '{slug}' not found",
                }
            },
        )

    return ArticleResponse(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        content_md=article.content_md,
        author=article.author.display_name or article.author.username if article.author else None,
        author_id=str(article.author_id) if article.author_id else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat(),
        current_version=article.current_version,
        byte_size=article.byte_size or 0,
        token_count_est=article.token_count_est or 0,
    )


# --- Update Article ---


@router.patch(
    "/articles/{slug}",
    response_model=ArticleResponse,
    status_code=status.HTTP_200_OK,
)
async def update_article(
    slug: str,
    data: UpdateArticleRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("library:edit")),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ArticleResponse:
    """
    Update an article.

    Requires If-Match header with current version for optimistic concurrency control.
    """
    user, _ = auth

    # Require If-Match header
    if if_match is None:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "error": {
                    "code": "PRECONDITION_REQUIRED",
                    "message": "If-Match header required for updates",
                }
            },
        )

    # Parse version from If-Match
    try:
        expected_version = int(if_match)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "If-Match header must be a version number",
                }
            },
        )

    # Fetch article
    result = await db.execute(
        select(Article).options(selectinload(Article.author)).where(Article.slug == slug)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Article '{slug}' not found",
                }
            },
        )

    # Check version
    if article.current_version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": f"Version mismatch: expected {expected_version}, current is {article.current_version}",
                }
            },
        )

    # Create revision before updating
    revision = ArticleRevision(
        article_id=article.id,
        version=article.current_version,
        title=article.title,
        content_md=article.content_md,
        editor_id=user.id,
        edit_summary=data.edit_summary,
    )
    db.add(revision)

    # Update article
    if data.title is not None:
        article.title = data.title
    if data.content_md is not None:
        article.content_md = data.content_md

    article.current_version += 1
    article.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Re-fetch the article to get computed columns
    result = await db.execute(
        select(Article).options(selectinload(Article.author)).where(Article.id == article.id)
    )
    article = result.scalar_one()

    return ArticleResponse(
        id=str(article.id),
        slug=article.slug,
        title=article.title,
        content_md=article.content_md,
        author=article.author.display_name or article.author.username if article.author else None,
        author_id=str(article.author_id) if article.author_id else None,
        created_at=article.created_at.isoformat(),
        updated_at=article.updated_at.isoformat(),
        current_version=article.current_version,
        byte_size=article.byte_size or 0,
        token_count_est=article.token_count_est or 0,
    )


# --- Delete Article ---


@router.delete(
    "/articles/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_scope("library:delete")),
) -> None:
    """
    Delete an article.

    Requires library:delete scope (typically admin only).
    """
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Article '{slug}' not found",
                }
            },
        )

    await db.delete(article)
    await db.commit()


# --- Search ---


@router.get(
    "/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
)
async def search_articles(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
) -> SearchResponse:
    """
    Full-text search across articles.

    Searches title and content using PostgreSQL full-text search.
    """
    # Use plainto_tsquery for simple search
    # This converts plain text to a tsquery
    search_query = func.plainto_tsquery("english", q)

    # Build query with ranking
    # Note: Since tsv might not be populated, fall back to ILIKE search
    result = await db.execute(
        select(Article)
        .where(
            (Article.title.ilike(f"%{q}%")) | (Article.content_md.ilike(f"%{q}%"))
        )
        .order_by(Article.updated_at.desc())
        .limit(limit)
    )
    articles = list(result.scalars().all())

    items = [
        SearchResultItem(
            slug=article.slug,
            title=article.title,
            snippet=article.content_md[:200] + "..." if len(article.content_md) > 200 else article.content_md,
            rank=None,  # Would be ts_rank if using tsvector
            byte_size=article.byte_size or 0,
            token_count_est=article.token_count_est or 0,
        )
        for article in articles
    ]

    return SearchResponse(
        items=items,
        total_count=len(items),
    )


# --- Batch Read ---


@router.post(
    "/articles/batch-read",
    response_model=BatchReadResponse,
    status_code=status.HTTP_200_OK,
)
async def batch_read_articles(
    data: BatchReadRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> BatchReadResponse:
    """
    Read multiple articles by slug in a single request.

    Maximum 100 slugs per request.
    """
    if not data.slugs:
        return BatchReadResponse(items=[], missing=[])

    # Fetch all matching articles
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.author))
        .where(Article.slug.in_(data.slugs))
    )
    articles = {article.slug: article for article in result.scalars().all()}

    # Build response
    items = []
    missing = []

    for slug in data.slugs:
        article = articles.get(slug)
        if article:
            items.append(
                ArticleResponse(
                    id=str(article.id),
                    slug=article.slug,
                    title=article.title,
                    content_md=article.content_md,
                    author=article.author.display_name or article.author.username if article.author else None,
                    author_id=str(article.author_id) if article.author_id else None,
                    created_at=article.created_at.isoformat(),
                    updated_at=article.updated_at.isoformat(),
                    current_version=article.current_version,
                    byte_size=article.byte_size or 0,
                    token_count_est=article.token_count_est or 0,
                )
            )
        else:
            missing.append(slug)

    return BatchReadResponse(items=items, missing=missing)
