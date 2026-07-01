"""In-memory task store ported from Go internal/services/task_service.go."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from models import (
    Task,
    TaskNotFoundError,
    TaskPriority,
    TaskStatus,
    ValidationError,
)


class TaskStore:
    """Thread-safe in-memory task storage.

    Mirrors the Go ``TaskService`` — a ``dict[str, Task]`` guarded by a
    ``threading.Lock``.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._initialize_sample_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _initialize_sample_data(self) -> None:
        """Seed the store with the same two tasks the Go implementation uses."""
        self.create_task(
            {
                "title": "Implement Go REST API",
                "description": "Create REST API with Gin framework",
                "priority": "high",
                "tags": ["go", "rest", "api"],
            }
        )
        self.create_task(
            {
                "title": "Add gRPC support",
                "description": "Implement gRPC server with native Go support",
                "priority": "medium",
                "tags": ["go", "grpc", "protobuf"],
            }
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_task(self, data: dict[str, Any]) -> Task:
        """Create a new task from *data* and return it.

        Matches Go ``CreateTask``: generates UUID, defaults status to
        ``pending``, priority to ``medium`` when empty, tags to ``[]``
        when ``None``.
        """
        with self._lock:
            now = datetime.now(timezone.utc)

            priority_str = data.get("priority", "") or ""
            if not priority_str:
                priority_str = "medium"

            if not TaskPriority.is_valid(priority_str):
                raise ValidationError(f"invalid priority: {priority_str}")

            tags = data.get("tags")
            if tags is None:
                tags = []

            task = Task(
                id=str(uuid.uuid4()),
                title=data.get("title", ""),
                description=data.get("description", ""),
                status=TaskStatus.PENDING,
                priority=TaskPriority(priority_str),
                tags=tags,
                created_by="system",
                assigned_to=data.get("assigned_to"),
                created_at=now,
                updated_at=now,
                due_date=data.get("due_date"),
            )

            self._tasks[task.id] = task
            return task

    def update_task(self, task_id: str, data: dict[str, Any]) -> Task:
        """Update an existing task.  Only keys present in *data* are applied.

        Raises ``TaskNotFoundError`` or ``ValidationError``.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(f"task with ID {task_id} not found")

            if "title" in data:
                task.title = data["title"]
            if "description" in data:
                task.description = data["description"]

            if "status" in data:
                status_str = data["status"]
                if not TaskStatus.is_valid(status_str):
                    raise ValidationError(f"invalid status: {status_str}")
                task.status = TaskStatus(status_str)

                # Set completed_at when status transitions to completed
                if task.status == TaskStatus.COMPLETED and task.completed_at is None:
                    task.completed_at = datetime.now(timezone.utc)

            if "priority" in data:
                priority_str = data["priority"]
                if not TaskPriority.is_valid(priority_str):
                    raise ValidationError(f"invalid priority: {priority_str}")
                task.priority = TaskPriority(priority_str)

            if "tags" in data:
                task.tags = data["tags"]
            if "assigned_to" in data:
                task.assigned_to = data["assigned_to"]
            if "due_date" in data:
                task.due_date = data["due_date"]

            task.updated_at = datetime.now(timezone.utc)
            return task

    def update_task_status(self, task_id: str, status: str) -> Task:
        """Convenience wrapper — delegates to ``update_task``."""
        return self.update_task(task_id, {"status": status})

    def delete_task(self, task_id: str) -> None:
        """Remove a task.  Raises ``TaskNotFoundError`` if not found."""
        with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"task with ID {task_id} not found")
            del self._tasks[task_id]
