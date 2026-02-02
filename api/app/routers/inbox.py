"""Inbox router for notifications."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.notification import Notification
from app.models.user import APIKey, User
from app.schemas.inbox import (
    InboxSummaryResponse,
    ListNotificationsResponse,
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationItem,
)

router = APIRouter(prefix="/api/v1/inbox", tags=["Inbox"])


# --- Inbox Summary ---


@router.get(
    "/summary",
    response_model=InboxSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_inbox_summary(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> InboxSummaryResponse:
    """
    Get inbox summary for session start.

    Returns counts of unread and total notifications.
    """
    user, _ = auth

    # Get unread count
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    )
    unread_count = unread_result.scalar() or 0

    # Get total count
    total_result = await db.execute(
        select(func.count(Notification.id)).where(Notification.user_id == user.id)
    )
    total_count = total_result.scalar() or 0

    return InboxSummaryResponse(
        unread_count=unread_count,
        total_count=total_count,
    )


# --- List Notifications ---


@router.get(
    "/notifications",
    response_model=ListNotificationsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(default=False, description="Show only unread notifications"),
) -> ListNotificationsResponse:
    """
    List notifications with cursor-based pagination.

    Returns notifications ordered by created_at descending.
    """
    user, _ = auth

    query = select(Notification).where(Notification.user_id == user.id)

    # Filter unread only
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    # Apply cursor (cursor is the created_at timestamp)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(Notification.created_at < cursor_dt)
        except ValueError:
            pass  # Invalid cursor, ignore

    query = query.order_by(Notification.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    notifications = list(result.scalars().all())

    # Check if there are more items
    has_more = len(notifications) > limit
    if has_more:
        notifications = notifications[:limit]

    items = [
        NotificationItem(
            id=str(n.id),
            notification_type=n.notification_type,
            title=n.title,
            body=n.body,
            resource_type=n.resource_type,
            resource_id=str(n.resource_id) if n.resource_id else None,
            payload=n.payload or {},
            created_at=n.created_at.isoformat(),
            read_at=n.read_at.isoformat() if n.read_at else None,
        )
        for n in notifications
    ]

    next_cursor = notifications[-1].created_at.isoformat() if notifications and has_more else None

    return ListNotificationsResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


# --- Mark Notification as Read ---


@router.post(
    "/notifications/{notification_id}/read",
    response_model=MarkReadResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> MarkReadResponse:
    """Mark a single notification as read."""
    user, _ = auth

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Notification '{notification_id}' not found",
                }
            },
        )

    # Mark as read if not already
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)

    return MarkReadResponse(
        id=str(notification.id),
        read_at=notification.read_at.isoformat(),
    )


# --- Mark All Notifications as Read ---


@router.post(
    "/notifications/read-all",
    response_model=MarkAllReadResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> MarkAllReadResponse:
    """Mark all unread notifications as read."""
    user, _ = auth

    now = datetime.now(timezone.utc)

    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
        .returning(Notification.id)
    )

    # Count how many were marked
    marked_ids = list(result.scalars().all())
    await db.commit()

    return MarkAllReadResponse(marked_count=len(marked_ids))


# --- Delete Notification ---


@router.delete(
    "/notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> None:
    """Delete a notification."""
    user, _ = auth

    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Notification '{notification_id}' not found",
                }
            },
        )

    await db.delete(notification)
    await db.commit()
