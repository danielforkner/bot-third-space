"""Authentication router for user registration, login, and API key management."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import generate_api_key, get_key_prefix
from app.auth.jwt import create_tokens
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.models.user import APIKey, User, UserRole
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse

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
async def register(
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

    await db.commit()
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


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
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

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid username or password",
                }
            },
        )

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
