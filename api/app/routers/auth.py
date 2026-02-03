"""Authentication router for user registration, login, and API key management."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import generate_api_key, get_key_prefix
from app.auth.dependencies import get_current_user
from app.auth.jwt import create_tokens, decode_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.user import APIKey, User, UserRole
from app.schemas.auth import (
    ApiKeyInfo,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    ListApiKeysResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

DEFAULT_ROLES = [
    "library:read",
    "library:create",
    "library:edit",
    "bulletin:read",
    "bulletin:write",
]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/hour")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Create a new user account with first API key.

    Returns the plaintext API key - this is the only time it will be visible.
    """
    # Check for existing username or email (case-insensitive for email)
    existing = await db.execute(
        select(User).where((User.username == data.username) | (User.email.ilike(data.email)))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "Username or email already exists",
                }
            },
        )

    # Create user
    user = User(
        username=data.username,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        display_name=data.display_name,
    )
    db.add(user)
    await db.flush()  # Get user.id

    # Add default roles
    for role in DEFAULT_ROLES:
        db.add(UserRole(user_id=user.id, role=role))

    # Create initial API key
    plaintext_key, key_hash = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=get_key_prefix(plaintext_key),
        name="Initial key",
        scopes=DEFAULT_ROLES,
    )
    db.add(api_key)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CONFLICT",
                    "message": "Username or email already exists",
                }
            },
        )

    await db.refresh(user)

    return RegisterResponse(
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        api_key=plaintext_key,
        roles=DEFAULT_ROLES,
        api_key_scopes=DEFAULT_ROLES,
    )


LOCKOUT_THRESHOLD = 5  # Number of failed attempts before lockout
LOCKOUT_DURATION_MINUTES = 15  # Duration of lockout in minutes


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/15minutes")
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate user and set JWT tokens as HttpOnly cookies.

    Accepts username or email in the 'username' field.
    """
    # Find user by username or email (case-insensitive for email)
    result = await db.execute(
        select(User).where(
            or_(
                User.username == data.username,
                User.email.ilike(data.username),
            )
        )
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid username or password",
                }
            },
        )

    # Check if account is locked
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until <= now:
        user.locked_until = None
        user.failed_login_count = 0

    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "ACCOUNT_LOCKED",
                    "message": "Account is temporarily locked due to too many failed login attempts",
                }
            },
        )

    if not verify_password(data.password, user.password_hash):
        # Increment failed login count and record timestamp
        user.failed_login_count = (user.failed_login_count or 0) + 1
        user.last_failed_at = now

        # Check if we should lock the account
        if user.failed_login_count >= LOCKOUT_THRESHOLD:
            from datetime import timedelta

            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid username or password",
                }
            },
        )

    # Successful login - reset failed count, clear lockout, and record timestamp
    user.failed_login_count = 0
    user.locked_until = None
    user.last_successful_at = now
    await db.commit()

    # Create JWT tokens
    tokens = create_tokens(str(user.id))

    # Set HttpOnly cookies
    # Access token - short TTL matching token expiry
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Refresh token - longer TTL
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth/refresh",  # Only sent to refresh endpoint
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    return LoginResponse(
        user_id=str(user.id),
        username=user.username,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> RefreshResponse:
    """
    Refresh access token using refresh token from cookie.

    Issues new access and refresh tokens as HttpOnly cookies.
    """
    # Check if refresh token cookie is present
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Refresh token not provided",
                }
            },
        )

    # Decode and validate the refresh token
    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid or expired refresh token",
                }
            },
        )

    # Verify it's a refresh token (not access token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid token type",
                }
            },
        )

    # Get user from database to verify they still exist
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "User not found",
                }
            },
        )

    # Create new JWT tokens
    tokens = create_tokens(str(user.id))

    # Set HttpOnly cookies
    # Access token - short TTL matching token expiry
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Refresh token - longer TTL
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/v1/auth/refresh",  # Only sent to refresh endpoint
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    return RefreshResponse(
        user_id=str(user.id),
        username=user.username,
    )


# --- API Key Management Endpoints ---


@router.post(
    "/api-keys",
    response_model=CreateApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def create_api_key(
    request: Request,
    data: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> CreateApiKeyResponse:
    """
    Create a new API key for the authenticated user.

    The plaintext key is only returned once - store it securely!
    Scopes must be a subset of the user's roles.
    """
    user, current_api_key = auth

    # Get user's roles
    user_roles = {role.role for role in user.roles}

    # Determine scopes for new key
    if data.scopes is None:
        # Default to user's roles
        scopes = list(user_roles)
    else:
        # Validate requested scopes are subset of user's roles
        requested_scopes = set(data.scopes)
        if not requested_scopes.issubset(user_roles):
            invalid_scopes = requested_scopes - user_roles
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Cannot grant scopes you don't have: {', '.join(invalid_scopes)}",
                    }
                },
            )
        scopes = data.scopes

    # Generate new API key
    plaintext_key, key_hash = generate_api_key()
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=get_key_prefix(plaintext_key),
        name=data.name,
        scopes=scopes,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return CreateApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        api_key=plaintext_key,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at.isoformat(),
    )


@router.get(
    "/api-keys",
    response_model=ListApiKeysResponse,
    status_code=status.HTTP_200_OK,
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> ListApiKeysResponse:
    """
    List all active (non-revoked) API keys for the authenticated user.

    Does not include the key hash or plaintext key.
    """
    user, _ = auth

    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == user.id)
        .where(APIKey.revoked_at.is_(None))
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    items = [
        ApiKeyInfo(
            id=str(key.id),
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes or [],
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
            expires_at=key.expires_at.isoformat() if key.expires_at else None,
        )
        for key in api_keys
    ]

    return ListApiKeysResponse(items=items)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    auth: tuple[User, APIKey] = Depends(get_current_user),
) -> None:
    """
    Revoke an API key (soft delete).

    The key will no longer be usable for authentication.
    """
    user, _ = auth

    # Validate UUID format
    try:
        key_uuid = UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "API key not found",
                }
            },
        )

    # Find the key
    result = await db.execute(
        select(APIKey)
        .where(APIKey.id == key_uuid)
        .where(APIKey.user_id == user.id)
        .where(APIKey.revoked_at.is_(None))
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "API key not found",
                }
            },
        )

    # Soft delete by setting revoked_at
    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
