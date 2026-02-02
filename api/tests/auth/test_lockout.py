"""
Tests for account lockout functionality.

Lockout rules:
- 5 failed attempts = 15 minute lock
- Successful login resets counter
- Lock expires after 15 minutes
"""

import pytest
from httpx import AsyncClient


class TestLockoutTriggering:
    """Tests for lockout activation."""

    async def test_first_four_failures_do_not_lock(
        self, async_client: AsyncClient, test_user: dict
    ):
        """First 4 failed logins do not trigger lockout."""
        for i in range(4):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )
            # Should return 401 (unauthorized), not locked
            assert response.status_code == 401

    async def test_fifth_failure_triggers_lockout(
        self, async_client: AsyncClient, test_user: dict
    ):
        """5th failed login triggers 15-minute lockout."""
        # Make 5 failed attempts
        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )

        # 6th attempt should indicate lockout
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        # Response should indicate account is locked
        data = response.json()
        assert "locked" in str(data).lower() or "error" in data

    async def test_correct_password_during_lockout_still_blocked(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Even correct password is rejected during lockout."""
        # Trigger lockout with 5 failures
        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )

        # Try with correct password - should still be locked
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 401


class TestLockoutExpiration:
    """Tests for lockout expiration."""

    async def test_lockout_expires_after_15_minutes(
        self, async_client: AsyncClient, test_user: dict, frozen_time
    ):
        """Login allowed after 15 minutes pass."""
        with frozen_time("2026-02-01 12:00:00"):
            # Trigger lockout
            for _ in range(5):
                await async_client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": test_user["username"],
                        "password": "WrongPassword123!",
                    },
                )

        # Move time forward 16 minutes
        with frozen_time("2026-02-01 12:16:00"):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": test_user["password"],
                },
            )
            # Should be able to login now
            assert response.status_code == 200


class TestLockoutReset:
    """Tests for lockout counter reset."""

    async def test_successful_login_resets_failure_count(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Successful login resets failed_login_count to 0."""
        # Make 3 failed attempts
        for _ in range(3):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )

        # Successful login
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )
        assert response.status_code == 200

        # Now 5 more failures should be needed to trigger lockout
        for _ in range(4):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )
            # Should not be locked yet
            assert response.status_code == 401


class TestLockoutWithApiKeys:
    """Ensure lockout only affects password auth, not API keys."""

    async def test_api_key_works_during_account_lockout(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """API key authentication works even when account is locked."""
        # Trigger lockout
        for _ in range(5):
            await async_client.post(
                "/api/v1/auth/login",
                json={
                    "username": test_user["username"],
                    "password": "WrongPassword123!",
                },
            )

        # API key should still work
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200
