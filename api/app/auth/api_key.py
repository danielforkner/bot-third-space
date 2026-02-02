"""API key generation and hashing utilities.

Uses HMAC-SHA256 for hashing (not bcrypt) because:
- API keys are high-entropy (64 hex chars) - no need for slow hashing
- bcrypt would add ~100ms latency per request
- HMAC is what Stripe, GitHub, and AWS use for API keys
"""

import hashlib
import hmac
import secrets

from app.config import settings

API_KEY_PREFIX = "ts_live_"


def generate_api_key() -> tuple[str, str]:
    """
    Generate API key and its hash.

    Returns:
        Tuple of (plaintext_key, key_hash).
        The plaintext key should only be shown once to the user.
    """
    random_part = secrets.token_hex(32)
    plaintext_key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hash_api_key(plaintext_key)
    return plaintext_key, key_hash


def hash_api_key(key: str) -> str:
    """Hash API key using HMAC-SHA256 with server secret."""
    return hmac.new(
        settings.api_key_secret.encode(),
        key.encode(),
        hashlib.sha256,
    ).hexdigest()


def get_key_prefix(key: str) -> str:
    """Get first 12 chars of key for identification in listings."""
    return key[:12]
