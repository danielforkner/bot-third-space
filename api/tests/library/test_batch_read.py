"""
Tests for library batch-read endpoint:
- POST /api/v1/library/articles/batch-read
"""

import pytest
from httpx import AsyncClient


class TestBatchRead:
    """POST /api/v1/library/articles/batch-read tests."""

    async def test_batch_read_returns_200(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Batch read returns 200."""
        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": []},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 200

    async def test_batch_read_returns_multiple_articles(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Can read multiple articles at once."""
        # Create articles
        slugs = []
        for i in range(3):
            create_response = await async_client.post(
                "/api/v1/library/articles",
                json={
                    "title": f"Batch Article {i}",
                    "slug": f"batch-article-{i}",
                    "content_md": f"Content for article {i}",
                },
                headers=auth_headers(test_user["api_key"]),
            )
            slugs.append(create_response.json()["slug"])

        # Batch read
        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": slugs},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 3

    async def test_batch_read_includes_full_content(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Batch read includes full article content."""
        content = "Full batch read content here"
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Batch Content Test",
                "slug": "batch-content-test",
                "content_md": content,
            },
            headers=auth_headers(test_user["api_key"]),
        )
        slug = create_response.json()["slug"]

        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": [slug]},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()
        assert data["items"][0]["content_md"] == content

    async def test_batch_read_handles_missing_articles(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Missing articles are indicated in response."""
        # Create one real article
        create_response = await async_client.post(
            "/api/v1/library/articles",
            json={
                "title": "Real Article",
                "slug": "real-batch-article",
                "content_md": "Real content",
            },
            headers=auth_headers(test_user["api_key"]),
        )
        real_slug = create_response.json()["slug"]

        # Request real and non-existent articles
        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": [real_slug, "nonexistent-slug"]},
            headers=auth_headers(test_user["api_key"]),
        )
        data = response.json()

        # Should return the found article
        found_slugs = [item["slug"] for item in data.get("items", [])]
        assert real_slug in found_slugs

        # Should indicate missing
        assert "missing" in data or len(data.get("items", [])) == 1

    async def test_batch_read_limit_100(
        self, async_client: AsyncClient, test_user: dict, auth_headers
    ):
        """Batch read rejects more than 100 slugs."""
        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": [f"slug-{i}" for i in range(101)]},
            headers=auth_headers(test_user["api_key"]),
        )
        assert response.status_code == 422  # Pydantic validation error

    async def test_batch_read_requires_auth(
        self, async_client: AsyncClient
    ):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/library/articles/batch-read",
            json={"slugs": ["test"]},
        )
        assert response.status_code == 401
