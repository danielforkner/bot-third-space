"""Tests for POST /api/v1/auth/refresh endpoint."""

import pytest
from freezegun import freeze_time
from datetime import datetime, timedelta

from app.auth.jwt import create_refresh_token, create_access_token


class TestRefreshSuccess:
    """Tests for successful token refresh scenarios."""

    async def test_refresh_with_valid_token_returns_200(
        self, async_client, test_user
    ):
        """Valid refresh token should return 200 OK."""
        # First login to get the refresh token
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        assert login_response.status_code == 200

        # Extract refresh token from login response cookies
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # Set the refresh token cookie and call refresh endpoint
        async_client.cookies.set("refresh_token", refresh_token)
        refresh_response = await async_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200

    async def test_refresh_sets_new_access_token_cookie(
        self, async_client, test_user
    ):
        """Refresh should set a new access_token cookie."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        refresh_token = login_response.cookies.get("refresh_token")
        async_client.cookies.set("refresh_token", refresh_token)

        # Refresh
        response = await async_client.post("/api/v1/auth/refresh")

        # Check that access_token cookie is set
        assert "access_token" in response.cookies

    async def test_refresh_sets_new_refresh_token_cookie(
        self, async_client, test_user
    ):
        """Refresh should set a new refresh_token cookie."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        refresh_token = login_response.cookies.get("refresh_token")
        async_client.cookies.set("refresh_token", refresh_token)

        # Refresh
        response = await async_client.post("/api/v1/auth/refresh")

        # Check that refresh_token cookie is set
        assert "refresh_token" in response.cookies

    async def test_refresh_returns_user_info(self, async_client, test_user):
        """Refresh response should include user_id and username."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        refresh_token = login_response.cookies.get("refresh_token")
        async_client.cookies.set("refresh_token", refresh_token)

        # Refresh
        response = await async_client.post("/api/v1/auth/refresh")
        data = response.json()

        assert "user_id" in data
        assert data["username"] == test_user["username"]

    async def test_refresh_cookies_are_httponly(self, async_client, test_user):
        """Refresh cookies should be HttpOnly for security."""
        # Login first
        login_response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
        )
        refresh_token = login_response.cookies.get("refresh_token")
        async_client.cookies.set("refresh_token", refresh_token)

        # Refresh
        response = await async_client.post("/api/v1/auth/refresh")

        # Check cookie headers for httponly flag
        set_cookie_headers = response.headers.get_list("set-cookie")
        for header in set_cookie_headers:
            if "access_token" in header or "refresh_token" in header:
                assert "httponly" in header.lower()


class TestRefreshFailure:
    """Tests for refresh failure scenarios."""

    async def test_refresh_without_cookie_returns_401(self, async_client):
        """Request without refresh_token cookie should return 401."""
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    async def test_refresh_with_invalid_token_returns_401(self, async_client):
        """Invalid refresh token should return 401."""
        async_client.cookies.set("refresh_token", "invalid_token")
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    async def test_refresh_with_access_token_returns_401(
        self, async_client, test_user
    ):
        """Using access token as refresh token should return 401."""
        # Create an access token (not refresh)
        access_token = create_access_token(test_user["user_id"])
        async_client.cookies.set("refresh_token", access_token)

        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    async def test_refresh_with_expired_token_returns_401(
        self, async_client, test_user
    ):
        """Expired refresh token should return 401."""
        # Create a token that expired in the past
        with freeze_time(datetime.now() - timedelta(days=8)):
            expired_token = create_refresh_token(test_user["user_id"])

        async_client.cookies.set("refresh_token", expired_token)
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    async def test_refresh_error_has_correct_format(self, async_client):
        """Error response should have standard error format."""
        response = await async_client.post("/api/v1/auth/refresh")
        data = response.json()

        assert "detail" in data
        assert "error" in data["detail"]
        assert "code" in data["detail"]["error"]
        assert "message" in data["detail"]["error"]

    async def test_refresh_with_nonexistent_user_returns_401(
        self, async_client, db_session
    ):
        """Refresh token for deleted user should return 401."""
        # Create token for a user ID that doesn't exist
        fake_user_id = "00000000-0000-0000-0000-000000000000"
        refresh_token = create_refresh_token(fake_user_id)
        async_client.cookies.set("refresh_token", refresh_token)

        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401
