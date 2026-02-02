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
