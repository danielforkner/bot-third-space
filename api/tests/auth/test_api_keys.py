"""
Tests for API key management endpoints:
- POST /api/v1/auth/api-keys (create)
- GET /api/v1/auth/api-keys (list)
- DELETE /api/v1/auth/api-keys/{id} (revoke)
"""

import pytest
from httpx import AsyncClient


class TestCreateApiKey:
    """POST /api/v1/auth/api-keys tests."""

    async def test_create_api_key_returns_201(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Creating API key returns 201."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201

    async def test_create_api_key_returns_plaintext_key(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes plaintext key (only time it's visible)."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data or "key" in data

    async def test_create_api_key_has_correct_prefix(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Returned key starts with 'ts_live_'."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201
        data = response.json()
        key = data.get("api_key") or data.get("key")
        assert key.startswith("ts_live_")

    async def test_create_api_key_with_custom_name(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can specify custom name for API key."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "My Custom Key Name"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert data.get("name") == "My Custom Key Name"

    async def test_create_api_key_with_subset_scopes(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can create key with subset of user's scopes."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Limited Key",
                "scopes": ["library:read", "bulletin:read"],
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert set(data.get("scopes", [])) == {"library:read", "bulletin:read"}

    async def test_create_api_key_fails_with_unowned_scope(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Cannot request scopes user doesn't have (returns 403)."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Admin Key Attempt",
                "scopes": ["admin"],
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_create_api_key_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Test Key"},
        )
        assert response.status_code == 401


class TestCreateApiKeyScopeValidation:
    """Scope inheritance validation tests."""

    async def test_non_admin_cannot_create_admin_scoped_key(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Regular user cannot create key with 'admin' scope."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Admin Key",
                "scopes": ["admin"],
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_admin_can_create_admin_scoped_key(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Admin user can create key with 'admin' scope."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Admin Key",
                "scopes": ["admin"],
            },
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 201

    async def test_user_without_delete_cannot_grant_delete(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """User without library:delete cannot create key with that scope."""
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={
                "name": "Delete Key",
                "scopes": ["library:delete"],
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403


class TestListApiKeys:
    """GET /api/v1/auth/api-keys tests."""

    async def test_list_api_keys_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Listing API keys returns 200."""
        response = await async_client.get(
            "/api/v1/auth/api-keys",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_api_keys_returns_array(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/auth/api-keys",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    async def test_list_api_keys_excludes_hash(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response does not include key_hash field."""
        response = await async_client.get(
            "/api/v1/auth/api-keys",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200
        data = response.json()
        keys = data.get("items", data) if isinstance(data, dict) else data
        for key in keys:
            assert "key_hash" not in key

    async def test_list_api_keys_includes_prefix(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes key_prefix for identification."""
        response = await async_client.get(
            "/api/v1/auth/api-keys",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200
        data = response.json()
        keys = data.get("items", data) if isinstance(data, dict) else data
        for key in keys:
            assert "key_prefix" in key

    async def test_list_api_keys_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/auth/api-keys")
        assert response.status_code == 401


class TestRevokeApiKey:
    """DELETE /api/v1/auth/api-keys/{id} tests."""

    async def test_revoke_api_key_returns_204(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Revoking own key returns 204."""
        # First create a key to revoke
        create_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Key to Revoke"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert create_response.status_code == 201
        key_id = create_response.json().get("id")

        # Now revoke it
        response = await async_client.delete(
            f"/api/v1/auth/api-keys/{key_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 204

    async def test_revoke_nonexistent_key_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Revoking non-existent key returns 404."""
        response = await async_client.delete(
            "/api/v1/auth/api-keys/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_revoke_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated revoke request returns 401."""
        response = await async_client.delete(
            "/api/v1/auth/api-keys/some-key-id",
        )
        assert response.status_code == 401


class TestApiKeyAuthentication:
    """Tests for API key authentication behavior."""

    async def test_valid_api_key_authenticates(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Valid API key in X-API-Key header authenticates."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_invalid_api_key_returns_401(
        self, async_client: AsyncClient, auth_headers
    ):
        """Invalid API key returns 401."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers("ts_live_invalid_key_that_does_not_exist"),
        )
        assert response.status_code == 401

    async def test_malformed_api_key_returns_401(
        self, async_client: AsyncClient, auth_headers
    ):
        """Malformed key (wrong prefix) returns 401."""
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers("wrong_prefix_key"),
        )
        assert response.status_code == 401

    async def test_missing_api_key_returns_401(
        self, async_client: AsyncClient
    ):
        """Missing API key returns 401."""
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401


class TestCreateApiKeyRateLimiting:
    """Rate limiting tests (10 per hour)."""

    @pytest.mark.slow
    async def test_create_api_key_rate_limit_allows_ten(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """First 10 key creations succeed."""
        for i in range(10):
            response = await async_client.post(
                "/api/v1/auth/api-keys",
                json={"name": f"Key {i}"},
                headers=auth_headers(test_user["api_key"]),
            )
            assert response.status_code == 201

    @pytest.mark.slow
    async def test_create_api_key_rate_limit_blocks_eleventh(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """11th creation returns 429 RATE_LIMITED."""
        # Create 10 keys first
        for i in range(10):
            await async_client.post(
                "/api/v1/auth/api-keys",
                json={"name": f"Key {i}"},
                headers=auth_headers(test_user["api_key"]),
            )

        # 11th should be rate limited
        response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Key 10"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 429
