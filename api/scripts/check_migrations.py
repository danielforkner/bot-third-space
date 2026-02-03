"""Fail if Alembic migrations are out of sync with SQLAlchemy models."""

from __future__ import annotations

import asyncio
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.config import settings
from app.database import Base
from app import models  # noqa: F401  # Ensure models are registered


def _compare(connection) -> list[object]:
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    return compare_metadata(context, Base.metadata)


async def main() -> int:
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        diffs = await conn.run_sync(_compare)
    await engine.dispose()

    if diffs:
        print("Detected schema differences between models and database:")
        for diff in diffs:
            print(diff)
        return 1

    print("No schema differences detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
