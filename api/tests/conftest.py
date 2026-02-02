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
from app.middleware.rate_limit import limiter

# Import models so they're registered with Base.metadata before table creation
from app.models.user import APIKey, User, UserRole
from app.auth.api_key import generate_api_key, get_key_prefix
from app.auth.password import hash_password

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


# --- Rate Limiter Reset Fixture ---


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test to ensure test isolation."""
    # Clear rate limiter storage before each test by clearing its internal storage dict
    # slowapi uses limits library with in-memory storage by default
    if hasattr(limiter, "_limiter") and limiter._limiter:
        storage = limiter._limiter.storage
        if hasattr(storage, "storage"):
            storage.storage.clear()
    yield


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


DEFAULT_ROLES = [
    "library:read",
    "library:create",
    "library:edit",
    "bulletin:read",
    "bulletin:write",
]

ADMIN_ROLES = DEFAULT_ROLES + ["library:delete", "admin"]


async def _create_user(
    db_session: AsyncSession,
    username: str,
    email: str,
    password: str,
    roles: list[str],
) -> dict[str, Any]:
    """Helper to create a user with roles and API key in the database."""
    # Create user
    user = User(
        username=username,
        email=email.lower(),
        password_hash=hash_password(password),
        display_name=username.title(),
    )
    db_session.add(user)
    await db_session.flush()

    # Add roles
    for role in roles:
        db_session.add(UserRole(user_id=user.id, role=role))

    # Create API key
    plaintext_key, key_hash = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=get_key_prefix(plaintext_key),
        name="Test key",
        scopes=roles,
    )
    db_session.add(api_key)

    await db_session.commit()
    await db_session.refresh(user)

    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "password": password,
        "api_key": plaintext_key,
        "roles": roles,
    }


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict[str, Any]:
    """
    Create a standard test user with default roles and an API key.

    Returns dict with user data and plaintext API key.
    """
    return await _create_user(
        db_session,
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
        roles=DEFAULT_ROLES,
    )


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> dict[str, Any]:
    """Create an admin user with all roles including 'admin'."""
    return await _create_user(
        db_session,
        username="adminuser",
        email="admin@example.com",
        password="AdminPassword123!",
        roles=ADMIN_ROLES,
    )


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> dict[str, Any]:
    """Create a second user for testing ownership/authorization scenarios."""
    return await _create_user(
        db_session,
        username="seconduser",
        email="second@example.com",
        password="SecondPassword123!",
        roles=DEFAULT_ROLES,
    )


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
