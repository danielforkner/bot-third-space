"""Admin-related Pydantic schemas."""

from pydantic import BaseModel


class AdminUserInfo(BaseModel):
    """User information for admin endpoints."""

    user_id: str
    username: str
    email: str | None
    display_name: str | None
    roles: list[str]
    created_at: str
    last_seen_at: str | None


class ListUsersResponse(BaseModel):
    """Response for GET /admin/users endpoint."""

    items: list[AdminUserInfo]


class UpdateRolesRequest(BaseModel):
    """Request to update a user's roles."""

    roles: list[str]


class UpdateRolesResponse(BaseModel):
    """Response after updating a user's roles."""

    user_id: str
    username: str
    roles: list[str]


class RevokeKeysResponse(BaseModel):
    """Response after revoking a user's API keys."""

    username: str
    revoked_count: int


class ActivityLogEntry(BaseModel):
    """Single activity log entry."""

    id: str
    timestamp: str
    user_id: str | None
    username: str | None
    action: str
    resource: str
    resource_id: str
    request_id: str | None
    ip_address: str | None


class ListActivityResponse(BaseModel):
    """Response for GET /admin/activity endpoint."""

    items: list[ActivityLogEntry]
    next_cursor: str | None = None
