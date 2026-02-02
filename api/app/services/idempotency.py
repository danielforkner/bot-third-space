"""Idempotency service for safe write operation retries."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey

# Idempotency keys expire after 24 hours
IDEMPOTENCY_TTL = timedelta(hours=24)


class IdempotencyService:
    """Service for handling idempotency keys on write operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_request_body(body: bytes) -> str:
        """Generate SHA256 hash of request body."""
        return hashlib.sha256(body).hexdigest()

    async def acquire_lock(
        self,
        key: str,
        user_id: UUID,
        method: str,
        path: str,
        request_hash: str,
    ) -> tuple[bool, dict | None]:
        """
        Attempt to acquire idempotency lock.

        Returns:
            (True, None) - Lock acquired, proceed with request
            (False, cached_response) - Request already completed, return cached

        Raises:
            HTTPException(409) - Conflict (different payload or in-progress)
        """
        now = datetime.now(timezone.utc)
        cutoff = now - IDEMPOTENCY_TTL

        # Try to insert with PROCESSING status
        try:
            new_key = IdempotencyKey(
                key=key,
                user_id=user_id,
                method=method,
                path=path,
                request_hash=request_hash,
                status="processing",
                created_at=now,
            )
            self.db.add(new_key)
            await self.db.flush()
            return (True, None)  # Lock acquired
        except IntegrityError:
            await self.db.rollback()
            # Key exists, check status

        # Key exists - fetch current state
        result = await self.db.execute(
            select(IdempotencyKey)
            .where(IdempotencyKey.key == key)
            .where(IdempotencyKey.user_id == user_id)
            .with_for_update()
        )
        record = result.scalar_one_or_none()

        if not record:
            # Shouldn't happen, but handle gracefully
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Idempotency key state error",
                    }
                },
            )

        # Check if expired - allow reuse
        if record.created_at < cutoff:
            await self.db.delete(record)
            await self.db.flush()

            # Create new entry
            new_key = IdempotencyKey(
                key=key,
                user_id=user_id,
                method=method,
                path=path,
                request_hash=request_hash,
                status="processing",
                created_at=now,
            )
            self.db.add(new_key)
            await self.db.flush()
            return (True, None)

        # Check for payload mismatch
        if (
            record.method != method
            or record.path != path
            or record.request_hash != request_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": "Idempotency key reused with different request",
                    }
                },
            )

        # Same request - check status
        if record.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "IDEMPOTENCY_IN_PROGRESS",
                        "message": "Request with this idempotency key is currently processing",
                    }
                },
            )

        if record.status == "completed":
            return (
                False,
                {
                    "body": record.response_body,
                    "status": record.response_status,
                },
            )

        # FAILED status - allow retry
        record.status = "processing"
        record.created_at = now
        await self.db.flush()
        return (True, None)

    async def complete(
        self,
        key: str,
        user_id: UUID,
        response: dict[str, Any],
        status_code: int,
    ) -> None:
        """Mark request as completed with cached response."""
        result = await self.db.execute(
            select(IdempotencyKey)
            .where(IdempotencyKey.key == key)
            .where(IdempotencyKey.user_id == user_id)
        )
        record = result.scalar_one_or_none()

        if record:
            record.status = "completed"
            record.response_body = response
            record.response_status = status_code
            record.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def fail(self, key: str, user_id: UUID) -> None:
        """Mark request as failed (allows retry with same key)."""
        result = await self.db.execute(
            select(IdempotencyKey)
            .where(IdempotencyKey.key == key)
            .where(IdempotencyKey.user_id == user_id)
        )
        record = result.scalar_one_or_none()

        if record:
            record.status = "failed"
            await self.db.flush()
