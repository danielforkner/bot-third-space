"""User-related Pydantic schemas."""

from pydantic import BaseModel


class UserMeResponse(BaseModel):
    """Response for GET /users/me endpoint."""

    user_id: str
    username: str
    email: str | None
    display_name: str | None
    roles: list[str]
    api_key_scopes: list[str]


class UserProfileResponse(BaseModel):
    """Public user profile response."""

    user_id: str
    username: str
    display_name: str | None
    created_at: str
    # Note: email is NOT included - it's private


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""

    display_name: str | None = None


class UpdateProfileResponse(BaseModel):
    """Response after updating profile."""

    user_id: str
    username: str
    display_name: str | None
