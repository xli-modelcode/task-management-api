"""Task models ported from Go internal/models/task.go."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, enum.Enum):
    """Represents the current state of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Return True if *value* is a recognised status string."""
        return value in cls._value2member_map_


class TaskPriority(str, enum.Enum):
    """Represents the priority level of a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Return True if *value* is a recognised priority string."""
        return value in cls._value2member_map_

    def get_value(self) -> int:
        """Return a numeric sort value for this priority."""
        return _PRIORITY_VALUES[self]


_PRIORITY_VALUES = {
    TaskPriority.LOW: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.HIGH: 3,
    TaskPriority.CRITICAL: 4,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_datetime(dt: datetime) -> str:
    """Format *dt* as RFC 3339 with a ``Z`` suffix (UTC).

    The Go reference implementation uses ``time.RFC3339`` which always
    renders UTC as ``Z`` rather than ``+00:00``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 / RFC 3339 string into a UTC datetime.

    Returns ``None`` when *value* is ``None``.  If *value* is already a
    ``datetime`` it is returned as-is.  Raises ``ValidationError`` on
    unparseable strings.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValidationError(f"expected datetime string, got {type(value).__name__}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"invalid datetime format: {value}") from exc
    return dt


def error_response(code: str, message: str) -> dict:
    """Build the standard error envelope matching Go's ``ErrorResponse``."""
    return {"error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Request / Response types (mirrors Go structs in internal/models/)
# ---------------------------------------------------------------------------

@dataclass
class CreateTaskRequest:
    """Body for ``POST /api/v1/tasks``.

    Mirrors Go ``CreateTaskRequest``.
    """

    title: str
    description: str = ""
    priority: str = ""
    tags: list[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


@dataclass
class UpdateTaskRequest:
    """Body for ``PUT /api/v1/tasks/<id>``.

    All fields are optional — only provided fields are applied.
    Mirrors Go ``UpdateTaskRequest``.
    """

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


@dataclass
class UpdateTaskStatusRequest:
    """Body for ``PATCH /api/v1/tasks/<id>/status``.

    Mirrors Go ``UpdateTaskStatusRequest``.
    """

    status: str = ""


@dataclass
class ErrorDetail:
    """Structured error detail inside an ``ErrorResponse``.

    Mirrors Go ``ErrorDetail``.
    """

    code: str = ""
    message: str = ""
    details: Optional[Any] = None

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict.

        Implements Go ``omitempty`` semantics: ``details`` is omitted when
        ``None``.
        """
        d: dict = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        return d


@dataclass
class ErrorResponse:
    """Standard error envelope returned by every error path.

    Mirrors Go ``ErrorResponse``.
    """

    error: ErrorDetail = field(default_factory=ErrorDetail)

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        return {"error": self.error.to_dict()}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TaskNotFoundError(Exception):
    """Raised when a task cannot be found by its ID."""


class ValidationError(Exception):
    """Raised when user-supplied data fails validation."""


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """Represents a task in the system."""

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    tags: list[str] = field(default_factory=list)
    created_by: str = "system"
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict.

        Implements Go ``omitempty`` semantics: ``assigned_to``,
        ``due_date``, and ``completed_at`` are **omitted** when ``None``.
        """
        d: dict = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }

        if self.assigned_to is not None:
            d["assigned_to"] = self.assigned_to
        if self.due_date is not None:
            d["due_date"] = format_datetime(self.due_date)
        if self.completed_at is not None:
            d["completed_at"] = format_datetime(self.completed_at)

        return d
