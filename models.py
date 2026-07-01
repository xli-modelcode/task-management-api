"""Task models ported from Go internal/models/task.go."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


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


def error_response(code: str, message: str) -> dict:
    """Build the standard error envelope matching Go's ``ErrorResponse``."""
    return {"error": {"code": code, "message": message}}


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
