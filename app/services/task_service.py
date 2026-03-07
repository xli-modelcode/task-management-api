"""
Task service – in-memory CRUD operations.

Translated from internal/services/task_service.go (partial – CreateTask,
GetTask, DeleteTask, and sample-data initialisation for Milestone 1).
"""

import threading
import uuid
from datetime import datetime, timezone

from app.models.task import (
    CreateTaskRequest,
    Task,
    TaskPriority,
    TaskStatus,
)


class TaskService:
    """Provides task management operations backed by a thread-safe in-memory store."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.tasks: dict[str, Task] = {}
        self._initialize_sample_data()

    # ------------------------------------------------------------------
    # Sample data (mirrors Go initializeSampleData)
    # ------------------------------------------------------------------

    def _initialize_sample_data(self) -> None:
        """Seed the store with the same sample tasks as the Go service."""
        sample_tasks = [
            CreateTaskRequest(
                title="Implement Go REST API",
                description="Create REST API with Gin framework",
                priority=TaskPriority.high,
                tags=["go", "rest", "api"],
            ),
            CreateTaskRequest(
                title="Add gRPC support",
                description="Implement gRPC server with native Go support",
                priority=TaskPriority.medium,
                tags=["go", "grpc", "protobuf"],
            ),
        ]
        for req in sample_tasks:
            self.create_task(req)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def create_task(self, req: CreateTaskRequest) -> Task:
        """Create a new task from a request.

        Mirrors Go CreateTask: generates UUID, defaults priority to medium,
        initialises empty tags, sets status to pending, created_by to 'system'.

        Raises ValueError for invalid priority.
        """
        with self._lock:
            now = datetime.now(timezone.utc)

            priority = req.priority if req.priority is not None else TaskPriority.medium

            # Validate priority (enum already constrains values, but mirror Go
            # behaviour for any edge-case callers)
            if not priority.is_valid():
                raise ValueError(f"invalid priority: {priority.value}")

            tags = req.tags if req.tags is not None else []

            task = Task(
                id=str(uuid.uuid4()),
                title=req.title,
                description=req.description,
                status=TaskStatus.pending,
                priority=priority,
                tags=tags,
                created_by="system",
                assigned_to=req.assigned_to,
                created_at=now,
                updated_at=now,
                due_date=req.due_date,
            )

            self.tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task by its ID.

        Raises ValueError if the task is not found (matches Go error message).
        """
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"task with ID {task_id} not found")
            return task

    def delete_task(self, task_id: str) -> None:
        """Delete a task by its ID.

        Raises ValueError if the task is not found (matches Go error message).
        """
        with self._lock:
            if task_id not in self.tasks:
                raise ValueError(f"task with ID {task_id} not found")
            del self.tasks[task_id]
