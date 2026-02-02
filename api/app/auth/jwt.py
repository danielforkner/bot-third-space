"""JWT token creation and validation for human sessions."""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings


def create_access_token(user_id: str) -> str:
    """Create a short-lived access token (15 minutes)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token (7 days)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_tokens(user_id: str) -> dict[str, str]:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
    }


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Returns the payload if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.JWTError:
        return None
