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
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.bulletin import router as bulletin_router
from app.routers.library import router as library_router
from app.routers.users import router as users_router

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
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(library_router)
app.include_router(bulletin_router)


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


# Note: Auth endpoints are implemented in routers/auth.py
# Note: /users/me is implemented in routers/users.py


# Note: Bulletin endpoints are implemented in routers/bulletin.py
# Note: User endpoints are implemented in routers/users.py


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


# Note: Admin endpoints are implemented in routers/admin.py
# GET /admin/activity is still a stub until activity logging is implemented
