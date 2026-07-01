"""In-memory task store ported from Go internal/services/task_service.go."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from models import (
    ListTasksQuery,
    ListTasksResponse,
    Task,
    TaskNotFoundError,
    TaskPriority,
    TaskStatus,
    ValidationError,
    parse_datetime,
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
    # Read operations
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> Task:
        """Return a task by its ID.

        Raises ``TaskNotFoundError`` if the task does not exist.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise TaskNotFoundError(f"task with ID {task_id} not found")
            return task

    def list_tasks(self, query: ListTasksQuery) -> ListTasksResponse:
        """Return a filtered, sorted, and paginated list of tasks."""
        with self._lock:
            tasks = list(self._tasks.values())

        # Apply filters
        tasks = self._filter_tasks(tasks, query)

        # Apply sorting
        tasks = self._sort_tasks(tasks, query.sort_order)

        # Apply pagination
        total_count = len(tasks)

        page_size = query.page_size
        if page_size <= 0:
            page_size = 20
        if page_size > 100:
            page_size = 100

        start_index = 0
        if query.page_token != "":
            try:
                start_index = int(query.page_token)
            except (ValueError, TypeError):
                start_index = 0

        end_index = start_index + page_size
        if end_index > total_count:
            end_index = total_count

        paginated_tasks: list[Task] = []
        if start_index < total_count:
            paginated_tasks = tasks[start_index:end_index]

        next_page_token = ""
        if end_index < total_count:
            next_page_token = str(end_index)

        return ListTasksResponse(
            tasks=paginated_tasks,
            next_page_token=next_page_token,
            total_count=total_count,
        )

    # ------------------------------------------------------------------
    # Write operations
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
                due_date=parse_datetime(data.get("due_date")),
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
                task.due_date = parse_datetime(data["due_date"])

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _filter_tasks(
        self, tasks: list[Task], query: ListTasksQuery
    ) -> list[Task]:
        """Apply status, assigned_to, and tag filters (AND-logic for tags)."""
        filtered: list[Task] = []

        for task in tasks:
            # Filter by status
            if query.status != "" and task.status.value != query.status:
                continue

            # Filter by assigned user
            if query.assigned_to != "":
                if task.assigned_to is None or task.assigned_to != query.assigned_to:
                    continue

            # Filter by tags (AND-logic: task must have ALL specified tags)
            if query.tags != "":
                tag_list = [t.strip() for t in query.tags.split(",")]
                has_all_tags = True
                for tag in tag_list:
                    if tag not in task.tags:
                        has_all_tags = False
                        break
                if not has_all_tags:
                    continue

            filtered.append(task)

        return filtered

    def _sort_tasks(self, tasks: list[Task], sort_order: str) -> list[Task]:
        """Sort tasks based on the specified order.

        For due_date sorting, None values sort to the END in both
        ascending and descending order (nil-last), matching the Go
        comparator behaviour.
        """
        if sort_order == "created_at_asc":
            return sorted(tasks, key=lambda t: t.created_at)
        elif sort_order == "created_at_desc":
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)
        elif sort_order == "due_date_asc":
            # Nil-last: tasks with due_date=None sort AFTER all others
            return sorted(
                tasks,
                key=lambda t: (
                    t.due_date is None,
                    t.due_date if t.due_date is not None else datetime.max.replace(tzinfo=timezone.utc),
                ),
            )
        elif sort_order == "due_date_desc":
            # Nil-last: tasks with due_date=None sort AFTER all others
            with_due = [t for t in tasks if t.due_date is not None]
            without_due = [t for t in tasks if t.due_date is None]
            with_due.sort(key=lambda t: t.due_date, reverse=True)  # type: ignore[arg-type]
            return with_due + without_due
        elif sort_order == "priority_asc":
            return sorted(tasks, key=lambda t: t.priority.get_value())
        elif sort_order == "priority_desc":
            return sorted(
                tasks, key=lambda t: t.priority.get_value(), reverse=True
            )

        # Unrecognized or empty sort_order: return as-is
        return tasks
