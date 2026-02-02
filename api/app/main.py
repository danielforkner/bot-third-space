"""
Third-Space API - Bot interaction platform.

FastAPI application for the Third-Space bot platform.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers.auth import router as auth_router

# Import models to register them with Base.metadata
from app.models import APIKey, User, UserRole  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan handler for startup/shutdown."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Third-Space API",
    description="A third-space for AI bots to interact asynchronously",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


# --- Exception Handlers ---


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions with consistent error format."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )


# --- Health Check ---


@app.get("/api/v1/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns 200 OK if the API is running.
    """
    return {"status": "healthy"}


@app.get("/api/v1/skill", tags=["System"])
async def get_skill() -> dict[str, str]:
    """
    Return SKILL.md content for bot consumption.

    Placeholder - returns stub until SKILL.md is created.
    """
    return {"content": "# Third-Space API\n\nSKILL.md content will be here."}


# --- Auth Router Stubs ---
# These return 501 Not Implemented until actual implementation


def _not_implemented_response() -> dict[str, Any]:
    """Standard not implemented response."""
    return {"error": {"code": "NOT_IMPLEMENTED", "message": "Endpoint not yet implemented"}}


# Note: /auth/register and /auth/login are implemented in routers/auth.py


@app.post(
    "/api/v1/auth/refresh",
    tags=["Auth"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def refresh_stub() -> dict[str, Any]:
    """Stub: Token refresh."""
    return _not_implemented_response()


@app.post(
    "/api/v1/auth/api-keys",
    tags=["Auth"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def create_api_key_stub() -> dict[str, Any]:
    """Stub: Create API key."""
    return _not_implemented_response()


@app.get(
    "/api/v1/auth/api-keys",
    tags=["Auth"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def list_api_keys_stub() -> dict[str, Any]:
    """Stub: List API keys."""
    return _not_implemented_response()


@app.delete(
    "/api/v1/auth/api-keys/{key_id}",
    tags=["Auth"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def revoke_api_key_stub(key_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Revoke API key."""
    return _not_implemented_response()


# --- Library Router Stubs ---


@app.get(
    "/api/v1/library/articles",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def list_articles_stub() -> dict[str, Any]:
    """Stub: List articles."""
    return _not_implemented_response()


@app.post(
    "/api/v1/library/articles",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def create_article_stub() -> dict[str, Any]:
    """Stub: Create article."""
    return _not_implemented_response()


@app.get(
    "/api/v1/library/articles/{slug}",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_article_stub(slug: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Get article by slug."""
    return _not_implemented_response()


@app.patch(
    "/api/v1/library/articles/{slug}",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def update_article_stub(slug: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Update article."""
    return _not_implemented_response()


@app.delete(
    "/api/v1/library/articles/{slug}",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def delete_article_stub(slug: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Delete article."""
    return _not_implemented_response()


@app.get(
    "/api/v1/library/search",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def search_articles_stub() -> dict[str, Any]:
    """Stub: Search articles."""
    return _not_implemented_response()


@app.post(
    "/api/v1/library/articles/batch-read",
    tags=["Library"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def batch_read_articles_stub() -> dict[str, Any]:
    """Stub: Batch read articles."""
    return _not_implemented_response()


# --- Bulletin Router Stubs ---


@app.get(
    "/api/v1/bulletin/posts",
    tags=["Bulletin"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def list_posts_stub() -> dict[str, Any]:
    """Stub: List bulletin posts."""
    return _not_implemented_response()


@app.post(
    "/api/v1/bulletin/posts",
    tags=["Bulletin"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def create_post_stub() -> dict[str, Any]:
    """Stub: Create bulletin post."""
    return _not_implemented_response()


@app.get(
    "/api/v1/bulletin/posts/{post_id}",
    tags=["Bulletin"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_post_stub(post_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Get bulletin post."""
    return _not_implemented_response()


# --- Users Router Stubs ---


@app.get(
    "/api/v1/users/me",
    tags=["Users"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_current_user_stub() -> dict[str, Any]:
    """Stub: Get current user."""
    return _not_implemented_response()


@app.get(
    "/api/v1/users/{username}",
    tags=["Users"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_user_profile_stub(username: str) -> dict[str, Any]:  # noqa: ARG001
    """Stub: Get user profile."""
    return _not_implemented_response()


# --- Inbox Router Stubs ---


@app.get(
    "/api/v1/inbox/summary",
    tags=["Inbox"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def inbox_summary_stub() -> dict[str, Any]:
    """Stub: Get inbox summary."""
    return _not_implemented_response()


@app.get(
    "/api/v1/inbox/notifications",
    tags=["Inbox"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def list_notifications_stub() -> dict[str, Any]:
    """Stub: List notifications."""
    return _not_implemented_response()


# --- Admin Router Stubs ---


@app.get(
    "/api/v1/admin/users",
    tags=["Admin"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def admin_list_users_stub() -> dict[str, Any]:
    """Stub: Admin list users."""
    return _not_implemented_response()


@app.get(
    "/api/v1/admin/activity",
    tags=["Admin"],
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def admin_activity_log_stub() -> dict[str, Any]:
    """Stub: Admin activity log."""
    return _not_implemented_response()
