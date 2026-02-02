"""
Tests for library article endpoints:
- GET /api/v1/library/articles (list)
- POST /api/v1/library/articles (create)
- GET /api/v1/library/articles/{slug} (read)
- PATCH /api/v1/library/articles/{slug} (update)
- DELETE /api/v1/library/articles/{slug} (delete)
"""

import pytest
from httpx import AsyncClient


class TestListArticles:
    """GET /api/v1/library/articles tests."""

    async def test_list_articles_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Authenticated user can list articles."""
        response = await async_client.get(
            "/api/v1/library/articles",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_list_articles_returns_items_array(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/library/articles",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_list_articles_includes_pagination(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes pagination info."""
        response = await async_client.get(
            "/api/v1/library/articles",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "has_more" in data or "next_cursor" in data

    async def test_list_articles_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/library/articles")
        assert response.status_code == 401


class TestCreateArticle:
    """POST /api/v1/library/articles tests."""

    async def test_create_article_returns_201(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can create an article."""
        response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Test Article",
                "content_md": "# Test\n\nThis is test content.",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201

    async def test_create_article_returns_slug(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes generated slug."""
        response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "My Amazing Article",
                "content_md": "Content here",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "slug" in data
        assert data["slug"]  # Not empty

    async def test_create_article_with_custom_slug(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can create article with custom slug."""
        response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Custom Slug Article",
                "slug": "my-custom-slug",
                "content_md": "Content here",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-custom-slug"

    async def test_create_article_duplicate_slug_returns_409(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Duplicate slug returns 409 Conflict."""
        # Create first article
        await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "First Article",
                "slug": "duplicate-slug",
                "content_md": "First content",
            },
            headers=auth_headers(test_user["api_key"]),
        )

        # Try to create second with same slug
        response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Second Article",
                "slug": "duplicate-slug",
                "content_md": "Second content",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 409

    async def test_create_article_invalid_slug_returns_422(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Invalid slug format returns 422."""
        response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Test",
                "slug": "Invalid Slug!",
                "content_md": "Content",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 422

    async def test_create_article_includes_metadata(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes byte_size and token_count_est."""
        content = "A" * 100  # 100 bytes
        response = await async_client.post(
            "/api/v1/library/articles",
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

    async def test_create_article_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test", "content_md": "Content"},
        )
        assert response.status_code == 401

    async def test_create_article_requires_library_create_scope(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Requires library:create scope."""
        # Create a key with only library:read scope
        key_response = await async_client.post(
            "/api/v1/auth/api-keys",
            json={"name": "Read Only", "scopes": ["library:read"]},
            headers=auth_headers(test_user["api_key"]),
        )
        read_only_key = key_response.json()["api_key"]

        response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test", "content_md": "Content"},
            headers=auth_headers(read_only_key),
        )
        assert response.status_code == 403


class TestGetArticle:
    """GET /api/v1/library/articles/{slug} tests."""

    async def test_get_article_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can get an article by slug."""
        # Create article first
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test Article", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        # Get it
        response = await async_client.get(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_get_article_returns_full_content(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes full article content."""
        content = "# Full Content\n\nThis is the full content."
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Full Content Test", "content_md": content},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        response = await async_client.get(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["content_md"] == content
        assert data["title"] == "Full Content Test"

    async def test_get_article_includes_version(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response includes current_version for concurrency control."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Version Test", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        response = await async_client.get(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "current_version" in data
        assert data["current_version"] == 1

    async def test_get_nonexistent_article_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Non-existent article returns 404."""
        response = await async_client.get(
            "/api/v1/library/articles/nonexistent-article-slug",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 404

    async def test_get_article_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/library/articles/some-slug")
        assert response.status_code == 401


class TestUpdateArticle:
    """PATCH /api/v1/library/articles/{slug} tests."""

    async def test_update_article_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can update an article."""
        # Create article first
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Original Title", "content_md": "Original content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        # Update it with If-Match header
        response = await async_client.patch(
            f"/api/v1/library/articles/{slug}",
            json={"title": "Updated Title"},
            headers={
                **auth_headers(test_user["api_key"]),
                "If-Match": "1",
            },
        )
        assert response.status_code == 200

    async def test_update_article_changes_content(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update actually changes the article."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Original", "content_md": "Original content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        await async_client.patch(
            f"/api/v1/library/articles/{slug}",
            json={"content_md": "New content"},
            headers={
                **auth_headers(test_user["api_key"]),
                "If-Match": "1",
            },
        )

        # Fetch again to verify
        get_response = await async_client.get(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert get_response.json()["content_md"] == "New content"

    async def test_update_article_increments_version(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update increments current_version."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Version Test", "content_md": "V1"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        update_response = await async_client.patch(
            f"/api/v1/library/articles/{slug}",
            json={"content_md": "V2"},
            headers={
                **auth_headers(test_user["api_key"]),
                "If-Match": "1",
            },
        )
        assert update_response.json()["current_version"] == 2

    async def test_update_article_requires_if_match(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update without If-Match header returns 428."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        response = await async_client.patch(
            f"/api/v1/library/articles/{slug}",
            json={"title": "New Title"},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 428

    async def test_update_article_version_mismatch_returns_409(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Wrong version in If-Match returns 409 Conflict."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        response = await async_client.patch(
            f"/api/v1/library/articles/{slug}",
            json={"title": "New Title"},
            headers={
                **auth_headers(test_user["api_key"]),
                "If-Match": "999",  # Wrong version
            },
        )
        assert response.status_code == 409

    async def test_update_nonexistent_article_returns_404(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Update non-existent article returns 404."""
        response = await async_client.patch(
            "/api/v1/library/articles/nonexistent-slug",
            json={"title": "New Title"},
            headers={
                **auth_headers(test_user["api_key"]),
                "If-Match": "1",
            },
        )
        assert response.status_code == 404

    async def test_update_article_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.patch(
            "/api/v1/library/articles/some-slug",
            json={"title": "New Title"},
        )
        assert response.status_code == 401


class TestDeleteArticle:
    """DELETE /api/v1/library/articles/{slug} tests."""

    async def test_delete_article_returns_204(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Can delete an article (requires library:delete)."""
        # Create article first
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "To Delete", "content_md": "Content"},
            headers=auth_headers(test_admin["api_key"]),
        )
        slug = create_response.json()["slug"]

        # Delete it
        response = await async_client.delete(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 204

    async def test_delete_article_removes_it(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Deleted article is no longer accessible."""
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "To Delete", "content_md": "Content"},
            headers=auth_headers(test_admin["api_key"]),
        )
        slug = create_response.json()["slug"]

        await async_client.delete(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_admin["api_key"]),
        )

        # Try to get it
        get_response = await async_client.get(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert get_response.status_code == 404

    async def test_delete_nonexistent_article_returns_404(
        self, async_client: AsyncClient, test_admin: dict, auth_headers
    ):
        """Delete non-existent article returns 404."""
        response = await async_client.delete(
            "/api/v1/library/articles/nonexistent-slug",
            headers=auth_headers(test_admin["api_key"]),
        )
        assert response.status_code == 404

    async def test_delete_requires_library_delete_scope(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Requires library:delete scope (regular user doesn't have it)."""
        # Create article
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={"title": "Test", "content_md": "Content"},
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        # Try to delete without library:delete scope
        response = await async_client.delete(
            f"/api/v1/library/articles/{slug}",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 403

    async def test_delete_article_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.delete("/api/v1/library/articles/some-slug")
        assert response.status_code == 401
