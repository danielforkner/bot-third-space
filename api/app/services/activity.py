"""Activity logging service for audit trail."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import ActivityLog

# Type aliases
ActionType = Literal["read", "create", "update", "delete"]
ResourceType = Literal[
    "article", "bulletin_post", "bulletin_comment", "profile", "user", "api_key"
]


class ActivityService:
    """Service for logging user activity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        request: Request,
        user_id: UUID | None,
        api_key_id: UUID | None,
        action: ActionType,
        resource: ResourceType,
        resource_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> ActivityLog:
        """
        Log an activity event.

        Args:
            request: FastAPI Request object (for IP, user-agent, request_id)
            user_id: ID of the user performing the action
            api_key_id: ID of the API key used (if any)
            action: Type of action (read, create, update, delete)
            resource: Type of resource being accessed
            resource_id: ID of the resource
            metadata: Optional additional context
        """
        # Extract HTTP context from request
        request_id = getattr(request.state, "request_id", None)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:512]  # Truncate to 512 chars

        log_entry = ActivityLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=metadata or {},
        )

        self.db.add(log_entry)
        # Don't commit here - let the caller handle the transaction
        return log_entry


async def log_activity(
    db: AsyncSession,
    request: Request,
    user_id: UUID | None,
    api_key_id: UUID | None,
    action: ActionType,
    resource: ResourceType,
    resource_id: UUID,
    metadata: dict[str, Any] | None = None,
) -> ActivityLog:
    """
    Convenience function to log activity without instantiating service.

    Usage in endpoints:
        await log_activity(
            db=db,
            request=request,
            user_id=user.id,
            api_key_id=api_key.id,
            action="create",
            resource="article",
            resource_id=article.id,
        )
    """
    service = ActivityService(db)
    return await service.log(
        request=request,
        user_id=user_id,
        api_key_id=api_key_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        metadata=metadata,
    )
