"""
FastAPI application entry-point.

Translated from cmd/rest-server/main.go – configures CORS, wires the
TaskService, includes routers, and provides the health endpoint.
"""

from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings

from app.routers import tasks as task_router
from app.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Configuration (mirrors Go PORT / GIN_MODE env vars)
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """Runtime configuration read from environment / .env file."""

    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Task Management API",
    version="1.0.0",
    debug=settings.debug,
)

# ---------------------------------------------------------------------------
# CORS – matches Go corsMiddleware() configuration
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Origin", "Content-Type", "Accept", "Authorization"],
)

# ---------------------------------------------------------------------------
# Shared service instance
# ---------------------------------------------------------------------------

task_service = TaskService()

# ---------------------------------------------------------------------------
# Custom exception handlers – return 400 (not 422) with Go error shape
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Override FastAPI's default 422 handler to return 400 with the
    canonical ``{"error": {"code": "VALIDATION_ERROR", "message": ...}}``
    envelope that the Go API uses."""
    # Build a single human-readable message from Pydantic errors
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = " -> ".join(str(part) for part in first.get("loc", []) if part != "body")
        msg = first.get("msg", str(exc))
        if loc:
            message = f"{loc}: {msg}"
        else:
            message = msg
    else:
        message = str(exc)

    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
            }
        },
    )


# ---------------------------------------------------------------------------
# Health endpoint (mirrors Go healthCheck handler)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "service": "task-api-go",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

task_router.register(app, task_service)

# ---------------------------------------------------------------------------
# Uvicorn entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
