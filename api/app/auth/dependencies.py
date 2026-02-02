"""Authentication dependencies for FastAPI endpoints."""

import asyncio
import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.api_key import hash_api_key
from app.database import AsyncSessionLocal, get_db
from app.models.user import APIKey, User, UserRole

# Minimum interval between last_used_at updates to reduce write amplification
LAST_USED_UPDATE_INTERVAL_SECONDS = 300  # 5 minutes


async def get_current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, APIKey]:
    """
    Validate API key and return the authenticated user and API key.

    Returns a tuple of (User, APIKey) so endpoints can access both
    the user info and the specific API key's scopes.

    Raises:
        HTTPException: 401 if API key is missing, invalid, or revoked
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "API key required",
                }
            },
        )

    # Validate key format
    if not x_api_key.startswith("ts_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid API key format",
                }
            },
        )

    # Hash the key and look it up
    key_hash = hash_api_key(x_api_key)

    result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user).selectinload(User.roles))
        .where(APIKey.key_hash == key_hash)
        .where(APIKey.revoked_at.is_(None))
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        # Constant-time comparison to prevent timing attacks
        # Even though the key wasn't found, we still perform a comparison
        # to ensure consistent response time regardless of key validity
        hmac.compare_digest(key_hash, "0" * 64)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or revoked API key",
                }
            },
        )

    # Check expiration if set
    now = datetime.now(timezone.utc)
    if api_key.expires_at is not None:
        if api_key.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "API key has expired",
                    }
                },
            )

    # Sampled last_used_at update to reduce write amplification
    # Only update if more than 5 minutes since last update
    if api_key.last_used_at is None or (
        now - api_key.last_used_at.replace(tzinfo=timezone.utc)
    ).total_seconds() > LAST_USED_UPDATE_INTERVAL_SECONDS:
        # Fire-and-forget background update with its own session
        asyncio.create_task(_update_last_used_at(api_key.id))

    return api_key.user, api_key


async def _update_last_used_at(api_key_id: UUID) -> None:
    """Background task to update last_used_at timestamp with its own session."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception:
        # Silently fail - this is a non-critical update
        pass


async def get_current_user_roles(
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> set[str]:
    """
    Get the set of roles for the current user.

    This returns the user's roles (not the API key's scopes).
    """
    user, _ = auth
    return {role.role for role in user.roles}


async def get_api_key_scopes(
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> set[str]:
    """
    Get the set of scopes for the current API key.

    API key scopes are always a subset of user roles.
    """
    _, api_key = auth
    return set(api_key.scopes or [])


async def require_admin(
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> tuple[User, APIKey]:
    """
    Require the authenticated user to have admin role.

    Raises:
        HTTPException: 403 if user doesn't have admin role
    """
    user, api_key = auth
    user_roles = {role.role for role in user.roles}

    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin access required",
                }
            },
        )

    return user, api_key
