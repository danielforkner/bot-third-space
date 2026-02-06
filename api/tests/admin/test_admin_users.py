"""
Tests for admin user management endpoints:
- GET /api/v1/admin/users (list all users)
- PATCH /api/v1/admin/users/{username}/roles (update user roles)
- POST /api/v1/admin/users/{username}/revoke-keys (revoke all user's API keys)
"""

from httpx import AsyncClient


class TestListUsers:
    """GET /api/v1/admin/users tests."""

    async def test_admin_can_list_users(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Admin user can list all users."""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_users_returns_array(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        assert "items" in data or isinstance(data, list)

    async def test_list_users_includes_user_info(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Response includes user details."""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        users = data.get("items", data) if isinstance(data, dict) else data

        # Should have at least 2 users (admin + test_user)
        assert len(users) >= 2

        # Check user fields
        for user in users:
            assert "user_id" in user or "id" in user
            assert "username" in user
            assert "email" in user
            assert "roles" in user

    async def test_list_users_excludes_password_hash(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Response does not include password_hash."""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        users = data.get("items", data) if isinstance(data, dict) else data

        for user in users:
            assert "password_hash" not in user
            assert "password" not in user

    async def test_non_admin_cannot_list_users(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Non-admin user gets 403 Forbidden."""
        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_list_users_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/admin/users")
        assert response.status_code == 401

    async def test_admin_key_without_admin_scope_cannot_list_users(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Admin user still needs an API key with admin scope."""
        create_key_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Limited Admin Key", "scopes": ["library:read"]},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert create_key_response.status_code == 201
        limited_key = create_key_response.json()["api_key"]

        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers(limited_key),
        )
        assert response.status_code == 403


class TestUpdateUserRoles:
    """PATCH /api/v1/admin/users/{username}/roles tests."""

    async def test_admin_can_update_user_roles(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Admin can update another user's roles."""
        response = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": ["library:read", "library:create"]},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200

    async def test_update_roles_returns_updated_user(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Response includes updated user with new roles."""
        new_roles = ["library:read", "bulletin:read"]
        response = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": new_roles},
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        assert set(data.get("roles", [])) == set(new_roles)

    async def test_admin_can_grant_admin_role(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Admin can grant admin role to another user."""
        response = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": ["admin", "library:read"]},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert "admin" in data.get("roles", [])

    async def test_update_nonexistent_user_returns_404(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Updating non-existent user returns 404."""
        response = await async_client.patch(
            "/api/v1/admin/users/nonexistent_user/roles",
            json={"roles": ["library:read"]},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 404

    async def test_non_admin_cannot_update_roles(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Non-admin user gets 403 Forbidden."""
        response = await async_client.patch(
            f"/api/v1/admin/users/{second_user['username']}/roles",
            json={"roles": ["library:read"]},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_update_roles_requires_auth(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": ["library:read"]},
        )
        assert response.status_code == 401

    async def test_update_roles_with_empty_list(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Can set roles to empty list (remove all roles)."""
        response = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": []},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("roles", ["not_empty"]) == []


class TestRevokeUserKeys:
    """POST /api/v1/admin/users/{username}/revoke-keys tests."""

    async def test_admin_can_revoke_user_keys(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Admin can revoke all of another user's API keys."""
        response = await async_client.post(
            f"/api/v1/admin/users/{test_user['username']}/revoke-keys",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 200

    async def test_revoke_keys_returns_count(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Response includes count of revoked keys."""
        response = await async_client.post(
            f"/api/v1/admin/users/{test_user['username']}/revoke-keys",
            headers=auth_headers(test_admin["api_key"]),
        )
        data = response.json()
        assert "revoked_count" in data

    async def test_revoked_keys_no_longer_work(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """After revocation, user's API keys no longer authenticate."""
        # Revoke all keys
        await async_client.post(
            f"/api/v1/admin/users/{test_user['username']}/revoke-keys",
            headers=auth_headers(test_admin["api_key"]),
        )

        # Try to use the old key
        response = await async_client.get(
            "/api/v1/users/me",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 401

    async def test_revoke_nonexistent_user_returns_404(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Revoking non-existent user's keys returns 404."""
        response = await async_client.post(
            "/api/v1/admin/users/nonexistent_user/revoke-keys",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 404

    async def test_non_admin_cannot_revoke_keys(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Non-admin user gets 403 Forbidden."""
        response = await async_client.post(
            f"/api/v1/admin/users/{second_user['username']}/revoke-keys",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_revoke_keys_requires_auth(
        self, async_client: AsyncClient, test_user: dict
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            f"/api/v1/admin/users/{test_user['username']}/revoke-keys",
        )
        assert response.status_code == 401


class TestRoleChangesAffectExistingKeys:
    """Role changes should immediately constrain existing API keys."""

    async def test_removed_role_revokes_existing_key_scope(
        self, async_client: AsyncClient, test_admin: dict, test_user: dict, auth_headers
    ):
        """Removing a role should disable that scope on previously issued keys."""
        # Existing key can create before role removal
        create_before = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Before Role Removal", "content_md": "ok"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert create_before.status_code == 201

        # Remove create/edit/write scopes from the user
        update_roles = await async_client.patch(
            f"/api/v1/admin/users/{test_user['username']}/roles",
            json={"roles": ["library:read", "bulletin:read"]},
            headers=auth_headers(test_admin["api_key"]),
        )
        assert update_roles.status_code == 200

        # Same API key should now be denied for library:create
        create_after = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "After Role Removal", "content_md": "still trying"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert create_after.status_code == 403
