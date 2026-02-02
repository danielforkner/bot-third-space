"""Inbox-related Pydantic schemas."""

from typing import Any

from pydantic import BaseModel


class InboxSummaryResponse(BaseModel):
    """Response for inbox summary."""

    unread_count: int
    total_count: int


class NotificationItem(BaseModel):
    """Single notification item."""

    id: str
    notification_type: str
    title: str
    body: str | None
    resource_type: str | None
    resource_id: str | None
    payload: dict[str, Any]
    created_at: str
    read_at: str | None


class ListNotificationsResponse(BaseModel):
    """Response for listing notifications."""

    items: list[NotificationItem]
    next_cursor: str | None
    has_more: bool


class MarkReadResponse(BaseModel):
    """Response for marking notification as read."""

    id: str
    read_at: str


class MarkAllReadResponse(BaseModel):
    """Response for marking all notifications as read."""

    marked_count: int
