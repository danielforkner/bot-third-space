"""
Tests for bulletin follow endpoints:
- POST /api/v1/bulletin/posts/{id}/follow (follow)
- DELETE /api/v1/bulletin/posts/{id}/follow (unfollow)
"""

import pytest
from httpx import AsyncClient


class TestFollowPost:
    """POST /api/v1/bulletin/posts/{id}/follow tests."""

    async def test_follow_post_returns_201(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can follow a post."""
        # Create post first
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Follow it
        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201

    async def test_follow_post_is_idempotent(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Following same post twice is idempotent (returns 200 or 201)."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Follow twice
        await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        response = await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        # Should succeed (200 or 201) not error
        assert response.status_code in [200, 201]

    async def test_follow_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Following non-existent post returns 404."""
        response = await async_client.post(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_follow_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/follow"
        )
        assert response.status_code == 401


class TestUnfollowPost:
    """DELETE /api/v1/bulletin/posts/{id}/follow tests."""

    async def test_unfollow_post_returns_204(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can unfollow a post."""
        # Create and follow post
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        await async_client.post(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )

        # Unfollow
        response = await async_client.delete(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 204

    async def test_unfollow_not_followed_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Unfollowing a post not followed returns 404."""
        create_response = await async_client.post(
            "/api/v1/bulletin/posts",
            json={"title": "Test Post", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        post_id = create_response.json()["id"]

        # Try to unfollow without following first
        response = await async_client.delete(
            f"/api/v1/bulletin/posts/{post_id}/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_unfollow_nonexistent_post_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Unfollowing non-existent post returns 404."""
        response = await async_client.delete(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/follow",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_unfollow_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.delete(
            "/api/v1/bulletin/posts/00000000-0000-0000-0000-000000000000/follow"
        )
        assert response.status_code == 401
