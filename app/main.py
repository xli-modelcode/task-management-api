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
    envelope that the Go API uses.

    Error messages are mapped to match Go/Gin binding-error format so that
    the REST contract stays identical across the two implementations.
    """
    errors = exc.errors()
    if errors:
        first = errors[0]
        error_type = first.get("type", "")
        loc = first.get("loc", ())
        msg = first.get("msg", str(exc))

        # Extract the field name, skipping the "body" prefix added by FastAPI
        field_parts = [str(p) for p in loc if p != "body"]
        field_name = field_parts[0] if field_parts else ""

        # --- Map to Go/Gin-style error messages ---

        if field_name == "title" and error_type in ("missing", "string_too_short"):
            # Go binding:"required,min=1" – both missing and empty-string
            # trigger the 'required' validator in Gin.
            message = (
                "Key: 'CreateTaskRequest.Title' Error:Field validation for "
                "'Title' failed on the 'required' tag"
            )
        elif error_type == "enum":
            # Go validates enums in the service layer with:
            #   fmt.Errorf("invalid <field>: %s", value)
            raw_value = first.get("input", "")
            message = f"invalid {field_name}: {raw_value}"
        else:
            # Fallback – keep the Pydantic-style message
            loc_str = " -> ".join(field_parts)
            if loc_str:
                message = f"{loc_str}: {msg}"
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
