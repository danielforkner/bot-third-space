"""
Tests for POST /api/v1/auth/register endpoint.

Registration creates a user account and returns the first API key.
"""

import pytest
from httpx import AsyncClient


class TestRegisterSuccess:
    """Happy path registration scenarios."""

    async def test_register_with_valid_data_returns_201(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """Registration with valid data creates user and returns 201."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert response.status_code == 201

    async def test_register_returns_api_key_with_correct_prefix(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """Returned API key starts with 'ts_live_' prefix."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("ts_live_")

    async def test_register_returns_user_info(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """Response includes user_id, username, email, display_name."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == valid_registration_data["username"]
        assert "email" in data
        assert data["email"] == valid_registration_data["email"]

    async def test_register_assigns_default_roles(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """New users receive default roles (library:read, etc.)."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "roles" in data
        expected_roles = [
            "library:read",
            "library:create",
            "library:edit",
            "bulletin:read",
            "bulletin:write",
        ]
        for role in expected_roles:
            assert role in data["roles"]

    async def test_register_api_key_has_default_scopes(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """Initial API key has all default scopes."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "api_key_scopes" in data or "scopes" in data

    async def test_register_without_display_name_succeeds(
        self, async_client: AsyncClient
    ):
        """Display name is optional."""
        data = {
            "username": "nodisplay",
            "email": "nodisplay@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 201


class TestRegisterValidation:
    """Input validation tests."""

    async def test_register_missing_username_returns_422(
        self, async_client: AsyncClient
    ):
        """Missing username field returns 422 VALIDATION_ERROR."""
        data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_missing_email_returns_422(
        self, async_client: AsyncClient
    ):
        """Missing email field returns 422 VALIDATION_ERROR."""
        data = {
            "username": "testuser",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_missing_password_returns_422(
        self, async_client: AsyncClient
    ):
        """Missing password field returns 422 VALIDATION_ERROR."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_invalid_username_format_returns_422(
        self, async_client: AsyncClient
    ):
        """Username not matching ^[a-z0-9_]{3,32}$ returns 422."""
        data = {
            "username": "Invalid-User!",  # Contains uppercase and special chars
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_username_too_short_returns_422(
        self, async_client: AsyncClient
    ):
        """Username under 3 chars returns 422."""
        data = {
            "username": "ab",  # Only 2 chars
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_username_too_long_returns_422(
        self, async_client: AsyncClient
    ):
        """Username over 32 chars returns 422."""
        data = {
            "username": "a" * 33,  # 33 chars
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_username_with_uppercase_returns_422(
        self, async_client: AsyncClient
    ):
        """Username with uppercase letters returns 422."""
        data = {
            "username": "TestUser",  # Contains uppercase
            "email": "test@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_invalid_email_format_returns_422(
        self, async_client: AsyncClient
    ):
        """Invalid email format returns 422."""
        data = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422

    async def test_register_weak_password_returns_422(
        self, async_client: AsyncClient
    ):
        """Password not meeting complexity requirements returns 422."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",  # Too short, no special chars
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422


class TestRegisterDuplicates:
    """Duplicate username/email tests."""

    async def test_register_duplicate_username_returns_409(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Duplicate username returns 409 CONFLICT."""
        data = {
            "username": test_user["username"],  # Same username
            "email": "different@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 409

    async def test_register_duplicate_email_returns_409(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Duplicate email returns 409 CONFLICT."""
        data = {
            "username": "differentuser",
            "email": test_user["email"],  # Same email
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 409

    async def test_register_case_insensitive_email_duplicate(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Email comparison is case-insensitive."""
        data = {
            "username": "differentuser",
            "email": test_user["email"].upper(),  # Same email, different case
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 409


class TestRegisterRateLimiting:
    """Rate limiting tests (5 per hour per IP)."""

    @pytest.mark.slow
    async def test_register_rate_limit_allows_first_five(
        self, async_client: AsyncClient
    ):
        """First 5 registrations from same IP succeed."""
        for i in range(5):
            data = {
                "username": f"ratelimituser{i}",
                "email": f"ratelimit{i}@example.com",
                "password": "SecurePassword123!",
            }
            response = await async_client.post("/api/v1/auth/register", json=data)
            assert response.status_code == 201

    @pytest.mark.slow
    async def test_register_rate_limit_blocks_sixth(
        self, async_client: AsyncClient
    ):
        """6th registration from same IP returns 429 RATE_LIMITED."""
        # First, make 5 registrations
        for i in range(5):
            data = {
                "username": f"ratelimituser{i}",
                "email": f"ratelimit{i}@example.com",
                "password": "SecurePassword123!",
            }
            await async_client.post("/api/v1/auth/register", json=data)

        # 6th should be rate limited
        data = {
            "username": "ratelimituser5",
            "email": "ratelimit5@example.com",
            "password": "SecurePassword123!",
        }
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 429

    async def test_register_rate_limit_includes_headers(
        self, async_client: AsyncClient, valid_registration_data: dict
    ):
        """Response includes X-RateLimit-* headers."""
        response = await async_client.post(
            "/api/v1/auth/register", json=valid_registration_data
        )
        assert "x-ratelimit-limit" in response.headers


class TestRegisterErrorFormat:
    """Error response format tests."""

    async def test_register_error_includes_error_object(
        self, async_client: AsyncClient
    ):
        """Error response has 'error' object with code and message."""
        data = {"username": "ab"}  # Invalid: missing required fields
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422
        error_data = response.json()
        assert "error" in error_data
        assert "code" in error_data["error"]
        assert "message" in error_data["error"]

    async def test_register_error_includes_request_id(
        self, async_client: AsyncClient
    ):
        """Error response has 'error.request_id' field."""
        data = {"username": "ab"}
        response = await async_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 422
        error_data = response.json()
        assert "error" in error_data
        assert "request_id" in error_data["error"]
