"""
Tests for library search endpoint:
- GET /api/v1/library/search
"""

import pytest
from httpx import AsyncClient


class TestSearch:
    """GET /api/v1/library/search tests."""

    async def test_search_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Search endpoint returns 200."""
        response = await async_client.get(
            "/api/v1/library/search?q=test",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_search_returns_items_array(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Response contains items array."""
        response = await async_client.get(
            "/api/v1/library/search?q=test",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    async def test_search_finds_matching_articles(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Search finds articles matching query."""
        # Create some articles
        await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Python Programming Guide",
                "slug": "python-guide",
                "content_md": "Learn Python programming from scratch.",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "JavaScript Basics",
                "slug": "js-basics",
                "content_md": "Introduction to JavaScript.",
            },
            headers=auth_headers(test_user["api_key"]),
        )

        # Search for Python
        response = await async_client.get(
            "/api/v1/library/search?q=python",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert len(data["items"]) >= 1
        assert any("python" in item["title"].lower() or "python" in item.get("slug", "").lower()
                   for item in data["items"])

    async def test_search_includes_metadata(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Search results include byte_size and token_count_est."""
        await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Searchable Article",
                "slug": "searchable-article",
                "content_md": "This is searchable content.",
            },
            headers=auth_headers(test_user["api_key"]),
        )

        response = await async_client.get(
            "/api/v1/library/search?q=searchable",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        if data["items"]:
            assert "byte_size" in data["items"][0]
            assert "token_count_est" in data["items"][0]

    async def test_search_respects_limit(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Search respects limit parameter."""
        # Create multiple articles
        for i in range(5):
            await async_client.post(
                "/api/v1/library/articles",
                json={
                    "title": f"Limited Article {i}",
                    "slug": f"limited-article-{i}",
                    "content_md": "Content for search limit testing.",
                },
                headers=auth_headers(test_user["api_key"]),
            )

        response = await async_client.get(
            "/api/v1/library/search?q=limited&limit=2",
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert len(data["items"]) <= 2

    async def test_search_requires_query_param(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Search without query parameter returns 422."""
        response = await async_client.get(
            "/api/v1/library/search",
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 422

    async def test_search_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/library/search?q=test")
        assert response.status_code == 401
