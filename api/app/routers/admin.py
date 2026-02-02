"""Admin router for user and system management."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models.user import APIKey, User, UserRole
from app.schemas.admin import (
    AdminUserInfo,
    ListActivityResponse,
    ListUsersResponse,
    RevokeKeysResponse,
    UpdateRolesRequest,
    UpdateRolesResponse,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=ListUsersResponse,
    status_code=status.HTTP_200_OK,
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_admin),
) -> ListUsersResponse:
    """
    List all users in the system.

    Requires admin role.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    items = [
        AdminUserInfo(
            user_id=str(user.id),
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            roles=[role.role for role in user.roles],
            created_at=user.created_at.isoformat(),
            last_seen_at=user.last_seen_at.isoformat() if user.last_seen_at else None,
        )
        for user in users
    ]

    return ListUsersResponse(items=items)


@router.patch(
    "/users/{username}/roles",
    response_model=UpdateRolesResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user_roles(
    username: str,
    data: UpdateRolesRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_admin),
) -> UpdateRolesResponse:
    """
    Update a user's roles.

    Requires admin role. Replaces all existing roles with the provided list.
    """
    # Find the user
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"User '{username}' not found",
                }
            },
        )

    # Delete existing roles
    for role in list(user.roles):
        await db.delete(role)

    # Add new roles
    for role_name in data.roles:
        db.add(UserRole(user_id=user.id, role=role_name))

    await db.commit()

    # Refresh to get updated roles
    await db.refresh(user)
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user.id)
    )
    user = result.scalar_one()

    return UpdateRolesResponse(
        user_id=str(user.id),
        username=user.username,
        roles=[role.role for role in user.roles],
    )


@router.post(
    "/users/{username}/revoke-keys",
    response_model=RevokeKeysResponse,
    status_code=status.HTTP_200_OK,
)
async def revoke_user_keys(
    username: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_admin),
) -> RevokeKeysResponse:
    """
    Revoke all API keys for a user.

    Requires admin role. This is a soft delete - keys are marked as revoked.
    """
    # Find the user
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"User '{username}' not found",
                }
            },
        )

    # Count and revoke all active keys
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(APIKey)
        .where(APIKey.user_id == user.id)
        .where(APIKey.revoked_at.is_(None))
        .values(revoked_at=now)
        .returning(APIKey.id)
    )
    revoked_ids = result.fetchall()
    revoked_count = len(revoked_ids)

    await db.commit()

    return RevokeKeysResponse(
        username=username,
        revoked_count=revoked_count,
    )


@router.get(
    "/activity",
    response_model=ListActivityResponse,
    status_code=status.HTTP_200_OK,
)
async def list_activity(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(require_admin),
    cursor: str | None = None,
    limit: int = 50,
) -> ListActivityResponse:
    """
    Get global activity log.

    Requires admin role. Returns cursor-paginated activity entries.

    Note: Activity logging is not yet fully implemented.
    This endpoint returns an empty list until the activity_log table
    and logging service are implemented.
    """
    # TODO: Implement activity logging
    # For now, return empty list as activity logging isn't implemented yet
    return ListActivityResponse(
        items=[],
        next_cursor=None,
    )
