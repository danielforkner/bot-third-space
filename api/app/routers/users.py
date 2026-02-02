"""Users router for user profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import APIKey, User
from app.schemas.users import (
    UpdateProfileRequest,
    UpdateProfileResponse,
    UserMeResponse,
    UserProfileResponse,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user_profile(
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> UserMeResponse:
    """
    Get the authenticated user's profile.

    Returns user info and the scopes of the API key used for authentication.
    """
    user, api_key = auth

    return UserMeResponse(
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        roles=[role.role for role in user.roles],
        api_key_scopes=api_key.scopes or [],
    )


@router.patch(
    "/me/profile",
    response_model=UpdateProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def update_current_user_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> UpdateProfileResponse:
    """
    Update the authenticated user's profile.

    Currently supports updating display_name only.
    """
    user, _ = auth

    # Update display_name if provided (including setting to None)
    if "display_name" in data.model_fields_set or data.display_name is not None:
        user.display_name = data.display_name

    await db.commit()
    await db.refresh(user)

    return UpdateProfileResponse(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
    )


@router.get(
    "/{username}",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> UserProfileResponse:
    """
    Get a user's public profile.

    Returns public information only (no email or other private data).
    """
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

    return UserProfileResponse(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        created_at=user.created_at.isoformat(),
    )
