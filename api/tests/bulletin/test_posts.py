"""
Tests for bulletin post endpoints:
- GET /api/v1/bulletin/posts (list)
- POST /api/v1/bulletin/posts (create)
- GET /api/v1/bulletin/posts/{id} (read)
- PATCH /api/v1/bulletin/posts/{id} (update)
- DELETE /api/v1/bulletin/posts/{id} (delete)
"""

import pytest
from httpx import AsyncClient


class TestListPosts:
    """GET /api/v1/bulletin/posts tests."""

    async def test_list_posts_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Authenticated user can list posts."""
        response = await async_client.get(
            "/api/v1/bulletin/posts",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_posts_returns_items_array(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/bulletin/posts",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_posts_includes_pagination(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes pagination info."""
        response = await async_client.get(
            "/api/v1/bulletin/posts",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "has_more" in data or "next_cursor" in data

    async def test_list_posts_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/bulletin/posts")
        assert response.status_code == 401


class TestCreatePost:
    """POST /api/v1/bulletin/posts tests."""

    async def test_create_post_returns_201(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can create a post."""
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={
                "title": "Test Post",
                "content_md": "# Test\n\nThis is a test post.",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201

    async def test_create_post_returns_id(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes generated ID."""
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={
                "title": "ID Test Post",
                "content_md": "Content here",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "id" in data
        assert data["id"]  # Not empty

    async def test_create_post_includes_metadata(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes byte_size and token_count_est."""
        content = "A" * 100  # 100 bytes
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={
                "title": "Metadata Test",
                "content_md": content,
            },
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "byte_size" in data
        assert "token_count_est" in data
        assert data["byte_size"] == 100
        assert data["token_count_est"] == 25  # 100 / 4

    async def test_create_post_includes_author(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes author info."""
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={
                "title": "Author Test",
                "content_md": "Content",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "author" in data or "author_id" in data

    async def test_create_post_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test", "content_md": "Content"},
        )
        assert response.status_code == 401

    async def test_create_post_requires_bulletin_write_scope(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Requires bulletin:write scope."""
        # Create a key with only bulletin:read scope
        key_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Read Only", "scopes": ["bulletin:read"]},
            headers=auth_headers(test_user["api_key"]),
        )
        read_only_key = key_response.json()["api_key"]

        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test", "content_md": "Content"},
            headers=auth_headers(read_only_key),
        )
        assert response.status_code == 403

    async def test_create_post_missing_title_returns_422(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Missing title returns 422."""
        response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"content_md": "Content only"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 422


class TestGetPost:
    """GET /api/v1/bulletin/posts/{id} tests."""

    async def test_get_post_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can get a post by ID."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Get it
        response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_get_post_returns_full_content(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes full post content."""
        content = "# Full Content\n\nThis is the full content."
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Full Content Test", "content_md": content},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["content_md"] == content
        assert data["title"] == "Full Content Test"

    async def test_get_post_includes_comments(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes comments array."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Comments Test", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "comments" in data
        assert isinstance(data["comments"], list)

    async def test_get_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Non-existent post returns 404."""
        response = await async_client.get(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_get_post_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestUpdatePost:
    """PATCH /api/v1/bulletin/posts/{id} tests."""

    async def test_update_post_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can update a post."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Original Title", "content_md": "Original content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Update it
        response = await async_client.patch(
            f"/api/v1/bulletin/posts/{post_id}",
            json={"title": "Updated Title"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_update_post_changes_content(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update actually changes the post."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Original", "content_md": "Original content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        await async_client.patch(
            f"/api/v1/bulletin/posts/{post_id}",
            json={"content_md": "New content"},
            headers=auth_headers(test_user["api_key"]),
        )

        # Fetch again to verify
        get_response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert get_response.json()["content_md"] == "New content"

    async def test_update_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update non-existent post returns 404."""
        response = await async_client.patch(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000",
            json={"title": "New Title"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_update_post_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.patch(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000",
            json={"title": "New Title"},
        )
        assert response.status_code == 401

    async def test_update_others_post_returns_403(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Cannot update another user's post."""
        # Create post as test_user
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Try to update as second_user
        response = await async_client.patch(
            f"/api/v1/bulletin/posts/{post_id}",
            json={"title": "Hacked Title"},
            headers=auth_headers(second_user["api_key"]),
        )
        assert response.status_code == 403


class TestDeletePost:
    """DELETE /api/v1/bulletin/posts/{id} tests."""

    async def test_delete_post_returns_204(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can delete own post."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "To Delete", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Delete it
        response = await async_client.delete(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 204

    async def test_delete_post_removes_it(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Deleted post is no longer accessible."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "To Delete", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        await async_client.delete(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )

        # Try to get it
        get_response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert get_response.status_code == 404

    async def test_delete_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Delete non-existent post returns 404."""
        response = await async_client.delete(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_delete_others_post_returns_403(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Cannot delete another user's post."""
        # Create post as test_user
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Try to delete as second_user
        response = await async_client.delete(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(second_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_delete_post_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.delete(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401
