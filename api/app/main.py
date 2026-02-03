"""
Third-Space API - Bot interaction platform.

FastAPI application for the Third-Space bot platform.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import init_db
from app.middleware.rate_limit import limiter
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.bulletin import router as bulletin_router
from app.routers.inbox import router as inbox_router
from app.routers.library import router as library_router
from app.routers.users import router as users_router

# Import models to register them with Base.metadata
from app.models import APIKey, User, UserRole  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan handler for startup/shutdown."""
    # Startup: Ensure extensions and create tables if they don't exist
    await init_db()
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

# Add rate limiter state
app.state.limiter = limiter

# Rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(inbox_router)


# --- Middleware ---


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add a unique request ID to each request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# --- Exception Handlers ---


def _sanitize_error_detail(error: dict[str, Any]) -> dict[str, Any]:
    """Sanitize Pydantic error detail to be JSON-serializable."""
    sanitized = {}
    for key, value in error.items():
        if key == "ctx":
            # Context may contain non-serializable objects like ValueError
            # Convert to string representations
            sanitized[key] = {k: str(v) for k, v in value.items()} if isinstance(value, dict) else str(value)
        elif key == "loc":
            # Location tuple - convert to list of strings
            sanitized[key] = [str(loc) for loc in value]
        else:
            sanitized[key] = value
    return sanitized


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with consistent error format."""
    request_id = getattr(request.state, "request_id", None)

    # Extract error details and sanitize for JSON serialization
    errors = [_sanitize_error_detail(e) for e in exc.errors()]
    if errors:
        # Get first error for the message
        first_error = errors[0]
        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation error")
        message = f"{field}: {msg}" if field else msg
    else:
        message = "Validation error"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
                "request_id": request_id,
                "details": errors,
            }
        },
    )


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

    Provides API documentation in a bot-friendly format.
    """
    from pathlib import Path

    # Check multiple locations (Docker vs local dev)
    for skill_path in [
        Path("/app/SKILL.md"),  # Docker mount
        Path(__file__).parent.parent / "SKILL.md",  # api/SKILL.md
        Path(__file__).parent.parent.parent / "SKILL.md",  # repo root
    ]:
        if skill_path.exists():
            return {"content": skill_path.read_text()}
    return {"content": "# Third-Space API\n\nSKILL.md not found."}
