"""
Tests for admin activity log endpoint:
- GET /api/v1/admin/activity
"""

from httpx import AsyncClient


class TestListActivity:
    """GET /api/v1/admin/activity tests."""

    async def test_admin_can_list_activity(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Admin user can access activity log."""
        response = await async_client.get(
            "/api/v1/admin/activity",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_activity_returns_items_array(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/admin/activity",
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_non_admin_cannot_list_activity(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Non-admin user gets 403 Forbidden."""
        response = await async_client.get(
            "/api/v1/admin/activity",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_list_activity_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/admin/activity")
        assert response.status_code == 401
