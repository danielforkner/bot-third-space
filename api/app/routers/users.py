"""Users router for user profile endpoints."""

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_user
from app.models.user import APIKey, User
from app.schemas.users import UserMeResponse

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
