"""Rate limiting middleware using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance with IP-based key function
# Note: headers_enabled requires Response parameter on all rate-limited endpoints,
# which is incompatible with our current setup. Rate limit headers would need
# a custom middleware implementation for per-API-key rate limiting.
limiter = Limiter(key_func=get_remote_address)


def get_limiter() -> Limiter:
    """Get the global limiter instance."""
    return limiter


def reset_limiter() -> None:
    """Reset the limiter storage. Used in tests to clear rate limit state."""
    if hasattr(limiter, "_limiter") and limiter._limiter:
        limiter._limiter.reset()
    # Also reset the storage directly if available
    if hasattr(limiter, "_storage") and limiter._storage:
        limiter._storage.reset()
