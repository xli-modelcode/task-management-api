"""
Task models and DTOs.

Translated from internal/models/task.go
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    """Represents the current state of a task."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    on_hold = "on_hold"

    def is_valid(self) -> bool:
        """Check whether the status value is a known member."""
        return self.value in {member.value for member in TaskStatus}


class TaskPriority(str, Enum):
    """Represents the priority level of a task."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

    def is_valid(self) -> bool:
        """Check whether the priority value is a known member."""
        return self.value in {member.value for member in TaskPriority}

    def get_value(self) -> int:
        """Return a numeric value for priority sorting (mirrors Go GetValue)."""
        _map = {
            TaskPriority.low: 1,
            TaskPriority.medium: 2,
            TaskPriority.high: 3,
            TaskPriority.critical: 4,
        }
        return _map.get(self, 2)


class SortOrder(str, Enum):
    """Represents the sort order for task listing."""

    created_at_asc = "created_at_asc"
    created_at_desc = "created_at_desc"
    due_date_asc = "due_date_asc"
    due_date_desc = "due_date_desc"
    priority_asc = "priority_asc"
    priority_desc = "priority_desc"


# ---------------------------------------------------------------------------
# Core Task model
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """Internal representation of a task (mirrors Go Task struct)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    description: str = ""
    status: TaskStatus
    priority: TaskPriority
    tags: list[str] = Field(default_factory=list)
    created_by: str = ""
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------

class CreateTaskRequest(BaseModel):
    """Request body for POST /api/v1/tasks (mirrors Go CreateTaskRequest)."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    priority: Optional[TaskPriority] = None
    tags: Optional[list[str]] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class UpdateTaskRequest(BaseModel):
    """Request body for PUT /api/v1/tasks/{id} (mirrors Go UpdateTaskRequest).

    All fields are optional; only provided fields are applied.
    """

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[list[str]] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class UpdateTaskStatusRequest(BaseModel):
    """Request body for PATCH /api/v1/tasks/{id}/status."""

    status: TaskStatus


class ListTasksQuery(BaseModel):
    """Query parameters for GET /api/v1/tasks."""

    page_size: int = Field(default=20, ge=1, le=100)
    page_token: Optional[str] = None
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    tags: Optional[str] = None
    sort_order: Optional[SortOrder] = None


class ListTasksResponse(BaseModel):
    """Response for GET /api/v1/tasks."""

    tasks: list[Task]
    next_page_token: Optional[str] = None
    total_count: int


# ---------------------------------------------------------------------------
# Error models
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Nested error detail (mirrors Go ErrorDetail)."""

    code: str
    message: str
    details: Optional[object] = None


class ErrorResponse(BaseModel):
    """Top-level error envelope (mirrors Go ErrorResponse)."""

    error: ErrorDetail
