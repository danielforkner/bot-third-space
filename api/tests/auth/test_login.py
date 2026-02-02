"""
Tests for POST /api/v1/auth/login endpoint.

Human login returns JWT tokens in HttpOnly cookies.
"""

import pytest
from httpx import AsyncClient


class TestLoginSuccess:
    """Happy path login scenarios."""

    async def test_login_with_valid_credentials_returns_200(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Login with correct username/password returns 200."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200

    async def test_login_sets_access_token_cookie(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Successful login sets 'access_token' HttpOnly cookie."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.cookies

    async def test_login_sets_refresh_token_cookie(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Successful login sets 'refresh_token' HttpOnly cookie."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        assert "refresh_token" in response.cookies

    async def test_login_access_cookie_is_httponly(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Access token cookie has HttpOnly flag."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower()

    async def test_login_access_cookie_is_samesite_strict(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Access token cookie has SameSite=Strict."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        assert "samesite=strict" in set_cookie.lower()

    async def test_login_returns_user_info(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Response body includes user_id and username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data

    async def test_login_with_email_succeeds(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Can login using email instead of username."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["email"],  # Using email
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200


class TestLoginFailure:
    """Authentication failure scenarios."""

    async def test_login_wrong_password_returns_401(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Wrong password returns 401 UNAUTHORIZED."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user_returns_401(
        self, async_client: AsyncClient
    ):
        """Non-existent username returns 401 UNAUTHORIZED."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistentuser",
                "password": "SomePassword123!",
            },
        )
        assert response.status_code == 401

    async def test_login_failure_does_not_set_cookies(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Failed login does not set any cookies."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "access_token" not in response.cookies
        assert "refresh_token" not in response.cookies


class TestLoginValidation:
    """Input validation tests."""

    async def test_login_missing_username_returns_422(
        self, async_client: AsyncClient
    ):
        """Missing username/email returns 422."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"password": "SomePassword123!"},
        )
        assert response.status_code == 422

    async def test_login_missing_password_returns_422(
        self, async_client: AsyncClient
    ):
        """Missing password returns 422."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testuser"},
        )
        assert response.status_code == 422

    async def test_login_empty_body_returns_422(
        self, async_client: AsyncClient
    ):
        """Empty request body returns 422."""
        response = await async_client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


class TestLoginRateLimiting:
    """Rate limiting tests (10 per 15 min per IP)."""

    @pytest.mark.slow
    async def test_login_rate_limit_allows_ten(
        self, async_client: AsyncClient, test_user: dict
    ):
        """First 10 login attempts from same IP succeed/fail normally."""
        for _ in range(10):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )
            assert response.status_code == 401  # Wrong password, not rate limited

    @pytest.mark.slow
    async def test_login_rate_limit_blocks_eleventh(
        self, async_client: AsyncClient, test_user: dict
    ):
        """11th attempt from same IP returns 429 RATE_LIMITED."""
        # Make 10 attempts first
        for _ in range(10):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )

        # 11th should be rate limited
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 429
