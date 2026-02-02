"""
Tests for user profile endpoints:
- GET /api/v1/users/me
- GET /api/v1/users/{username}
- PATCH /api/v1/users/me/profile
"""

import pytest
from httpx import AsyncClient


class TestGetCurrentUser:
    """GET /api/v1/users/me tests."""

    async def test_get_me_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Authenticated user can get their own profile."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_get_me_returns_user_info(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes user details."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()

        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]
        assert "user_id" in data
        assert "roles" in data

    async def test_get_me_includes_api_key_scopes(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes the scopes of the API key used."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()

        assert "api_key_scopes" in data
        assert isinstance(data["api_key_scopes"], list)

    async def test_get_me_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401


class TestGetUserProfile:
    """GET /api/v1/users/{username} tests."""

    async def test_get_user_profile_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can get another user's public profile."""
        response = await async_client.get(
            f"/api/v1/users/{test_user['username']}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_get_user_profile_returns_public_info(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Response includes public profile information."""
        response = await async_client.get(
            f"/api/v1/users/{second_user['username']}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()

        assert data["username"] == second_user["username"]
        assert "display_name" in data
        # Should NOT include sensitive info
        assert "email" not in data or data.get("email") is None
        assert "password_hash" not in data

    async def test_get_nonexistent_user_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Getting non-existent user returns 404."""
        response = await async_client.get(
            "/api/v1/users/nonexistent_user_12345",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_get_user_profile_requires_auth(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get(f"/api/v1/users/{test_user['username']}")
        assert response.status_code == 401


class TestUpdateProfile:
    """PATCH /api/v1/users/me/profile tests."""

    async def test_update_profile_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can update own profile."""
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "New Display Name"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_update_profile_changes_display_name(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Display name is updated."""
        new_name = "Updated Name"
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": new_name},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["display_name"] == new_name

    async def test_update_profile_persists(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Updated profile is persisted."""
        new_name = "Persistent Name"
        await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": new_name},
            headers=auth_headers(test_user["api_key"]),
        )

        # Fetch profile again
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["display_name"] == new_name

    async def test_update_profile_can_clear_display_name(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can set display_name to null."""
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": None},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["display_name"] is None

    async def test_update_profile_ignores_username(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Cannot change username via profile update."""
        original_username = test_user["username"]
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"username": "new_username"},
            headers=auth_headers(test_user["api_key"]),
        )
        # Should succeed but not change username
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == original_username

    async def test_update_profile_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "Test"},
        )
        assert response.status_code == 401
