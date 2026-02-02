"""Authentication dependencies for FastAPI endpoints."""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.api_key import hash_api_key
from app.database import get_db
from app.models.user import APIKey, User, UserRole


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
    if api_key.expires_at is not None:
        from datetime import datetime, timezone

        if api_key.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "API key has expired",
                    }
                },
            )

    return api_key.user, api_key


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
