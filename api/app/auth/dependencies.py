"""Authentication dependencies for FastAPI endpoints."""

import datetime as dt
import hmac
import re

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.api_key import hash_api_key
from app.database import get_db
from app.models.user import APIKey, User

# Minimum interval between last_used_at updates to reduce write amplification
LAST_USED_UPDATE_INTERVAL_SECONDS = 300  # 5 minutes
API_KEY_PATTERN = re.compile(r"^ts_live_[0-9a-f]{64}$")


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
    if not API_KEY_PATTERN.fullmatch(x_api_key):
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
    now = dt.datetime.now(dt.UTC)
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
    last_used_at = api_key.last_used_at
    if last_used_at is None:
        api_key.last_used_at = now
    else:
        last_used_utc = (
            last_used_at.astimezone(dt.UTC)
            if last_used_at.tzinfo is not None
            else last_used_at.replace(tzinfo=dt.UTC)
        )
        if (now - last_used_utc).total_seconds() > LAST_USED_UPDATE_INTERVAL_SECONDS:
            api_key.last_used_at = now

    return api_key.user, api_key


def get_effective_scopes(user: User, api_key: APIKey) -> set[str]:
    """Compute effective scopes as intersection of key scopes and current user roles."""
    user_roles = {role.role for role in user.roles}
    key_scopes = set(api_key.scopes or [])
    return key_scopes & user_roles


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

    Returns effective scopes (API key scopes intersected with current user roles).
    """
    user, api_key = auth
    return get_effective_scopes(user, api_key)


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
    effective_scopes = get_effective_scopes(user, api_key)

    if "admin" not in user_roles or "admin" not in effective_scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Admin role and scope required",
                }
            },
        )

    return user, api_key
