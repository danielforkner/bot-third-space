"""
Tests for inbox endpoints:
- GET /api/v1/inbox/summary
- GET /api/v1/inbox/notifications
- POST /api/v1/inbox/notifications/{id}/read
- POST /api/v1/inbox/notifications/read-all
- DELETE /api/v1/inbox/notifications/{id}
"""

import pytest
from httpx import AsyncClient


class TestInboxSummary:
    """GET /api/v1/inbox/summary tests."""

    async def test_summary_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Authenticated user can get inbox summary."""
        response = await async_client.get(
            "/api/v1/inbox/summary",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_summary_includes_unread_count(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Summary includes unread notification count."""
        response = await async_client.get(
            "/api/v1/inbox/summary",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)

    async def test_summary_includes_total_count(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Summary includes total notification count."""
        response = await async_client.get(
            "/api/v1/inbox/summary",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "total_count" in data
        assert isinstance(data["total_count"], int)

    async def test_summary_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/inbox/summary")
        assert response.status_code == 401


class TestListNotifications:
    """GET /api/v1/inbox/notifications tests."""

    async def test_list_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Authenticated user can list notifications."""
        response = await async_client.get(
            "/api/v1/inbox/notifications",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_returns_items_array(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/inbox/notifications",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_includes_pagination(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes pagination info."""
        response = await async_client.get(
            "/api/v1/inbox/notifications",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "has_more" in data or "next_cursor" in data

    async def test_list_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/inbox/notifications")
        assert response.status_code == 401

    async def test_list_filter_unread_only(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can filter to show only unread notifications."""
        response = await async_client.get(
            "/api/v1/inbox/notifications?unread_only=true",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200


class TestMarkAsRead:
    """POST /api/v1/inbox/notifications/{id}/read tests."""

    async def test_mark_read_nonexistent_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Marking non-existent notification returns 404."""
        response = await async_client.post(
            "/api/v1/inbox/notifications/00000000-0000-0000-0000-000000000000/read",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_mark_read_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/inbox/notifications/00000000-0000-0000-0000-000000000000/read"
        )
        assert response.status_code == 401


class TestMarkAllAsRead:
    """POST /api/v1/inbox/notifications/read-all tests."""

    async def test_mark_all_read_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can mark all notifications as read."""
        response = await async_client.post(
            "/api/v1/inbox/notifications/read-all",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_mark_all_read_returns_count(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes count of marked notifications."""
        response = await async_client.post(
            "/api/v1/inbox/notifications/read-all",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "marked_count" in data

    async def test_mark_all_read_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post("/api/v1/inbox/notifications/read-all")
        assert response.status_code == 401


class TestDeleteNotification:
    """DELETE /api/v1/inbox/notifications/{id} tests."""

    async def test_delete_nonexistent_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Deleting non-existent notification returns 404."""
        response = await async_client.delete(
            "/api/v1/inbox/notifications/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_delete_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.delete(
            "/api/v1/inbox/notifications/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestNotificationWorkflow:
    """End-to-end notification workflow tests."""

    async def test_notification_workflow(
        self, async_client: AsyncClient, test_user: dict, auth_headers, db_session
    ):
        """Test creating, reading, marking read, and deleting a notification."""
        from app.models.notification import Notification

        # Create a notification directly in the database
        notification = Notification(
            user_id=test_user["user_id"],
            notification_type="test",
            title="Test Notification",
            body="This is a test notification",
        )
        db_session.add(notification)
        await db_session.commit()
        await db_session.refresh(notification)
        notification_id = str(notification.id)

        # Check summary shows unread
        summary_response = await async_client.get(
            "/api/v1/inbox/summary",
            headers=auth_headers(test_user["api_key"]),
        )
        assert summary_response.json()["unread_count"] >= 1

        # List notifications
        list_response = await async_client.get(
            "/api/v1/inbox/notifications",
            headers=auth_headers(test_user["api_key"]),
        )
        assert any(n["id"] == notification_id for n in list_response.json()["items"])

        # Mark as read
        read_response = await async_client.post(
            f"/api/v1/inbox/notifications/{notification_id}/read",
            headers=auth_headers(test_user["api_key"]),
        )
        assert read_response.status_code == 200

        # Delete
        delete_response = await async_client.delete(
            f"/api/v1/inbox/notifications/{notification_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert delete_response.status_code == 204

        # Verify deleted
        get_response = await async_client.get(
            "/api/v1/inbox/notifications",
            headers=auth_headers(test_user["api_key"]),
        )
        assert not any(n["id"] == notification_id for n in get_response.json()["items"])
