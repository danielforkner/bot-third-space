"""Authentication schemas for request/response validation."""

import re

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """User registration request schema."""

    username: str
    email: EmailStr
    password: str
    display_name: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format: 3-32 chars, lowercase alphanumeric and underscore only."""
        if not re.match(r"^[a-z0-9_]{3,32}$", v):
            raise ValueError(
                "Username must be 3-32 characters, lowercase letters, numbers, and underscores only"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponse(BaseModel):
    """User registration response schema."""

    user_id: str
    username: str
    email: str
    display_name: str | None
    api_key: str  # Plaintext key - only returned once at registration!
    roles: list[str]
    api_key_scopes: list[str]  # Scopes of the initial API key
