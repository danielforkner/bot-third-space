"""
Shared test fixtures for Third-Space API tests.

Provides database session management, test clients, and user fixtures.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Test database URL (uses separate test database)
TEST_DATABASE_URL = settings.test_database_url

# Create test engine with NullPool to avoid connection issues
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# --- Event Loop Fixture ---


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# --- Database Fixtures ---


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create tables before each test function, drop after.
    Provides isolated database state per test.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client configured for testing.
    Overrides database dependency with test session.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    app.dependency_overrides.clear()


# --- Authentication Helper Fixtures ---


@pytest.fixture
def auth_headers():
    """Factory fixture for creating X-API-Key headers."""

    def _auth_headers(api_key: str) -> dict[str, str]:
        return {"X-API-Key": api_key}

    return _auth_headers


@pytest.fixture
def valid_registration_data() -> dict[str, str]:
    """Valid user registration payload."""
    return {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "display_name": "New User",
    }


@pytest.fixture
def valid_login_data() -> dict[str, str]:
    """Valid login payload (requires test_user to exist)."""
    return {
        "username": "testuser",
        "password": "TestPassword123!",
    }


# --- User Fixtures ---
# Note: These will be fully implemented once the User model exists.
# For now, they're placeholders that tests can reference.


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict[str, Any]:
    """
    Create a standard test user with default roles and an API key.

    Returns dict with user data and plaintext API key.

    Note: This fixture will be fully implemented once User model exists.
    Currently returns a mock structure for test development.
    """
    # Placeholder - will be implemented with actual model creation
    return {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "api_key": "ts_live_placeholder_key_for_testing",
        "roles": [
            "library:read",
            "library:create",
            "library:edit",
            "bulletin:read",
            "bulletin:write",
        ],
    }


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> dict[str, Any]:
    """
    Create an admin user with all roles including 'admin'.

    Note: This fixture will be fully implemented once User model exists.
    """
    return {
        "user_id": "00000000-0000-0000-0000-000000000002",
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "api_key": "ts_live_admin_placeholder_key",
        "roles": [
            "library:read",
            "library:create",
            "library:edit",
            "library:delete",
            "bulletin:read",
            "bulletin:write",
            "admin",
        ],
    }


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> dict[str, Any]:
    """
    Create a second user for testing ownership/authorization scenarios.

    Note: This fixture will be fully implemented once User model exists.
    """
    return {
        "user_id": "00000000-0000-0000-0000-000000000003",
        "username": "seconduser",
        "email": "second@example.com",
        "password": "SecondPassword123!",
        "api_key": "ts_live_second_placeholder_key",
        "roles": [
            "library:read",
            "library:create",
            "library:edit",
            "bulletin:read",
            "bulletin:write",
        ],
    }


# --- Utility Fixtures ---


@pytest.fixture
def idempotency_key():
    """Generate a unique idempotency key for testing."""
    import secrets

    def _idempotency_key(prefix: str = "test") -> str:
        return f"{prefix}-{secrets.token_hex(16)}"

    return _idempotency_key


@pytest.fixture
def frozen_time():
    """
    Fixture for time-based testing using freezegun.

    Usage:
        with frozen_time("2026-02-01 12:00:00"):
            # time is frozen
    """
    from freezegun import freeze_time

    return freeze_time
