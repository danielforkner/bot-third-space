"""
Health check endpoint tests.

This is the first test to pass - validates basic test infrastructure.
"""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    """Tests for GET /api/v1/health."""

    async def test_health_returns_200(self, async_client: AsyncClient):
        """Health check endpoint returns 200 OK."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_returns_healthy_status(self, async_client: AsyncClient):
        """Health check returns status: healthy."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    async def test_health_does_not_require_auth(self, async_client: AsyncClient):
        """Health check works without authentication."""
        # No auth headers provided
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200


class TestSkillEndpoint:
    """Tests for GET /api/v1/skill."""

    async def test_skill_returns_200(self, async_client: AsyncClient):
        """Skill endpoint returns 200 OK."""
        response = await async_client.get("/api/v1/skill")
        assert response.status_code == 200

    async def test_skill_returns_content(self, async_client: AsyncClient):
        """Skill endpoint returns content field."""
        response = await async_client.get("/api/v1/skill")
        data = response.json()
        assert "content" in data

    async def test_skill_content_is_string(self, async_client: AsyncClient):
        """Skill content is a string."""
        response = await async_client.get("/api/v1/skill")
        data = response.json()
        assert isinstance(data["content"], str)

    async def test_skill_does_not_require_auth(self, async_client: AsyncClient):
        """Skill endpoint works without authentication."""
        response = await async_client.get("/api/v1/skill")
        assert response.status_code == 200
