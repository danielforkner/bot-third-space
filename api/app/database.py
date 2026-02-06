"""Database configuration and session management."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from alembic.command import downgrade, upgrade
from alembic.config import Config
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


def _alembic_config(db_url: str | None = None) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)
    return config


def run_migrations(revision: str = "head", db_url: str | None = None) -> None:
    """Run Alembic migrations to a target revision."""
    config = _alembic_config(db_url)
    if revision == "base":
        downgrade(config, revision)
    else:
        upgrade(config, revision)


async def migrate_db(revision: str = "head", db_url: str | None = None) -> None:
    """Async wrapper to run migrations without blocking the event loop."""
    url = db_url or settings.database_url
    await asyncio.to_thread(run_migrations, revision, url)


async def init_db(db_url: str | None = None) -> None:
    """Initialize database schema via Alembic migrations."""
    await migrate_db("head", db_url)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
