"""
Tests for bulletin comment endpoints:
- POST /api/v1/bulletin/posts/{id}/comments (add comment)
"""

import pytest
from httpx import AsyncClient


class TestAddComment:
    """POST /api/v1/bulletin/posts/{id}/comments tests."""

    async def test_add_comment_returns_201(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can add a comment to a post."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Add comment
        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/comments",
            json={"content_md": "This is a comment."},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201

    async def test_add_comment_returns_id(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes comment ID."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/comments",
            json={"content_md": "Comment content"},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "id" in data
        assert data["id"]

    async def test_comment_appears_in_post(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Comment appears when fetching post."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        comment_content = "This is my comment"
        await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/comments",
            json={"content_md": comment_content},
            headers=auth_headers(test_user["api_key"]),
        )

        # Fetch post and check comments
        get_response = await async_client.get(
            f"/api/v1/bulletin/posts/{post_id}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = get_response.json()
        assert len(data["comments"]) >= 1
        assert any(c["content_md"] == comment_content for c in data["comments"])

    async def test_add_comment_to_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Adding comment to non-existent post returns 404."""
        response = await async_client.post(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/comments",
            json={"content_md": "Comment"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_add_comment_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/comments",
            json={"content_md": "Comment"},
        )
        assert response.status_code == 401

    async def test_add_comment_requires_bulletin_write_scope(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Requires bulletin:write scope."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Create a key with only bulletin:read scope
        key_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Read Only", "scopes": ["bulletin:read"]},
            headers=auth_headers(test_user["api_key"]),
        )
        read_only_key = key_response.json()["api_key"]

        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/comments",
            json={"content_md": "Comment"},
            headers=auth_headers(read_only_key),
        )
        assert response.status_code == 403

    async def test_different_user_can_comment(
        self, async_client: AsyncClient, test_user: dict, second_user: dict, auth_headers
    ):
        """Another user can comment on a post."""
        # Create post as test_user
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Comment as second_user
        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/comments",
            json={"content_md": "Comment from another user"},
            headers=auth_headers(second_user["api_key"]),
        )
        assert response.status_code == 201
