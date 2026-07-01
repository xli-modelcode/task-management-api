"""Tests for all task endpoints: POST, PUT, PATCH, DELETE, GET list, GET by id.

Each test gets a fresh app / store (via the ``client`` fixture), so
the store always starts with the two seeded sample tasks.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta

from models import TaskStatus, TaskPriority

# =====================================================================
# Helper
# =====================================================================

def _create_task(client, **overrides):
    """Shortcut: POST a new task and return (response, data)."""
    payload = {"title": "Test task", "description": "A test", **overrides}
    resp = client.post(
        "/api/v1/tasks",
        data=json.dumps(payload),
        content_type="application/json",
    )
    return resp, resp.get_json()


# =====================================================================
# POST /api/v1/tasks  — Create
# =====================================================================

class TestCreateTask:
    """POST /api/v1/tasks"""

    def test_valid_creation_returns_201_with_location(self, client):
        resp, data = _create_task(client, title="My new task", priority="high")
        assert resp.status_code == 201
        assert "Location" in resp.headers
        assert resp.headers["Location"] == f"/api/v1/tasks/{data['id']}"
        assert data["title"] == "My new task"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert data["created_by"] == "system"
        # created_at / updated_at must be RFC3339 with Z
        assert data["created_at"].endswith("Z")
        assert data["updated_at"].endswith("Z")

    def test_missing_title_returns_400(self, client):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps({"description": "no title"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_title_returns_400(self, client):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps({"title": "   "}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_title_over_200_chars_returns_400(self, client):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps({"title": "x" * 201}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_priority_returns_400(self, client):
        resp, data = _create_task(client, priority="ultra")
        assert resp.status_code == 400
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_default_priority_is_medium(self, client):
        resp, data = _create_task(client)
        assert resp.status_code == 201
        assert data["priority"] == "medium"

    def test_tags_default_to_empty_list(self, client):
        resp, data = _create_task(client)
        assert resp.status_code == 201
        assert data["tags"] == []

    def test_omitempty_fields_absent_when_none(self, client):
        """assigned_to, due_date, completed_at must be ABSENT, not null."""
        resp, data = _create_task(client)
        assert resp.status_code == 201
        assert "assigned_to" not in data
        assert "due_date" not in data
        assert "completed_at" not in data

    def test_create_with_due_date(self, client):
        resp, data = _create_task(client, due_date="2025-12-31T23:59:59Z")
        assert resp.status_code == 201
        assert data["due_date"] == "2025-12-31T23:59:59Z"

    def test_create_with_assigned_to(self, client):
        resp, data = _create_task(client, assigned_to="alice")
        assert resp.status_code == 201
        assert data["assigned_to"] == "alice"


# =====================================================================
# PUT /api/v1/tasks/<id>  — Update
# =====================================================================

class TestUpdateTask:
    """PUT /api/v1/tasks/<id>"""

    def test_partial_update_only_changes_provided_fields(self, client):
        # Create a task first
        resp, created = _create_task(client, title="Original", priority="low")
        task_id = created["id"]

        # Update only the title
        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"title": "Updated"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        updated = resp.get_json()
        assert updated["title"] == "Updated"
        # Priority should remain unchanged
        assert updated["priority"] == "low"

    def test_invalid_status_returns_400(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"status": "invalid_status"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_priority_returns_400(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"priority": "ultra"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_unknown_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.put(
            f"/api/v1/tasks/{fake_id}",
            data=json.dumps({"title": "nope"}),
            content_type="application/json",
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_update_due_date(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"due_date": "2025-06-15T12:00:00Z"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        updated = resp.get_json()
        assert updated["due_date"] == "2025-06-15T12:00:00Z"

    def test_completed_at_set_when_status_transitions_to_completed(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]
        assert "completed_at" not in created

        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        updated = resp.get_json()
        assert "completed_at" in updated
        assert updated["completed_at"].endswith("Z")


# =====================================================================
# PATCH /api/v1/tasks/<id>/status  — Update Status
# =====================================================================

class TestUpdateTaskStatus:
    """PATCH /api/v1/tasks/<id>/status"""

    def test_valid_status_transition(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.patch(
            f"/api/v1/tasks/{task_id}/status",
            data=json.dumps({"status": "in_progress"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "in_progress"

    def test_completed_at_set_when_completing(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.patch(
            f"/api/v1/tasks/{task_id}/status",
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "completed_at" in body
        assert body["completed_at"].endswith("Z")

    def test_invalid_status_returns_400(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.patch(
            f"/api/v1/tasks/{task_id}/status",
            data=json.dumps({"status": "flying"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"

    def test_unknown_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.patch(
            f"/api/v1/tasks/{fake_id}/status",
            data=json.dumps({"status": "pending"}),
            content_type="application/json",
        )
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"


# =====================================================================
# DELETE /api/v1/tasks/<id>
# =====================================================================

class TestDeleteTask:
    """DELETE /api/v1/tasks/<id>"""

    def test_valid_delete_returns_204(self, client):
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 204
        assert resp.data == b""

    def test_unknown_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/tasks/{fake_id}")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_deleted_task_not_found_on_subsequent_request(self, client):
        """After deletion, GET on the same ID should 404."""
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 204

        # GET on deleted ID -> 404
        resp = client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"


# =====================================================================
# GET /api/v1/tasks  — List (pagination)
# =====================================================================


class TestListTasksDefault:
    """Default request returns sample tasks with total_count."""

    def test_list_tasks_default(self, client):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 200

        data = resp.get_json()
        assert "tasks" in data
        assert "total_count" in data
        # The store is seeded with 2 sample tasks
        assert data["total_count"] == 2
        assert len(data["tasks"]) == 2


class TestListTasksCustomPageSize:
    """page_size=1 returns only 1 task and next_page_token."""

    def test_list_tasks_custom_page_size(self, client):
        resp = client.get("/api/v1/tasks?page_size=1")
        assert resp.status_code == 200

        data = resp.get_json()
        assert len(data["tasks"]) == 1
        assert "next_page_token" in data
        assert data["next_page_token"] != ""
        # total_count still reflects all matching tasks
        assert data["total_count"] == 2


class TestListTasksNextPageToken:
    """Pagination through multiple pages."""

    def test_list_tasks_next_page_token(self, client):
        # First page
        resp1 = client.get("/api/v1/tasks?page_size=1")
        assert resp1.status_code == 200
        data1 = resp1.get_json()
        assert len(data1["tasks"]) == 1
        assert "next_page_token" in data1
        next_token = data1["next_page_token"]

        # Second page using the token from first page
        resp2 = client.get(f"/api/v1/tasks?page_size=1&page_token={next_token}")
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert len(data2["tasks"]) == 1

        # The two pages should return different tasks
        assert data1["tasks"][0]["id"] != data2["tasks"][0]["id"]


class TestListTasksEmptyResults:
    """Filter by status no task has returns empty list."""

    def test_list_tasks_empty_results(self, client):
        resp = client.get("/api/v1/tasks?status=cancelled")
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["tasks"] == []
        assert data["total_count"] == 0


class TestListTasksInvalidPageSize:
    """Non-integer page_size returns 400."""

    def test_list_tasks_invalid_page_size(self, client):
        resp = client.get("/api/v1/tasks?page_size=abc")
        assert resp.status_code == 400

        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"


# =====================================================================
# GET /api/v1/tasks  — List (filtering)
# =====================================================================


class TestFilterByStatus:
    """Filter tasks by a specific status."""

    def test_filter_by_status(self, client, store):
        # Create a task via store and set its status to in_progress
        task = store.create_task({
            "title": "Status filter test",
            "description": "Testing status filter",
            "priority": "medium",
        })
        task.status = TaskStatus.IN_PROGRESS

        resp = client.get("/api/v1/tasks?status=in_progress")
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["total_count"] >= 1
        # Every returned task must have the filtered status
        for t in data["tasks"]:
            assert t["status"] == "in_progress"

        # Our seeded task should be in the results
        returned_ids = [t["id"] for t in data["tasks"]]
        assert task.id in returned_ids


class TestFilterByAssignedTo:
    """Filter tasks by assigned_to field."""

    def test_filter_by_assigned_to(self, client, store):
        task = store.create_task({
            "title": "Assigned to alice",
            "description": "Testing assigned_to filter",
            "priority": "low",
            "assigned_to": "alice",
        })

        resp = client.get("/api/v1/tasks?assigned_to=alice")
        assert resp.status_code == 200

        data = resp.get_json()
        assert data["total_count"] >= 1
        for t in data["tasks"]:
            assert t["assigned_to"] == "alice"

        returned_ids = [t["id"] for t in data["tasks"]]
        assert task.id in returned_ids


class TestFilterByTags:
    """AND-logic tag filtering."""

    def test_filter_by_tags(self, client, store):
        # The sample data already has a task with tags ["go", "rest", "api"]
        # and another with ["go", "grpc", "protobuf"].
        # Filtering by "go,rest" should only return tasks that have BOTH tags.

        resp = client.get("/api/v1/tasks?tags=go,rest")
        assert resp.status_code == 200

        data = resp.get_json()
        # Only the first sample task ("Implement Go REST API") has both "go" and "rest"
        assert data["total_count"] >= 1
        for t in data["tasks"]:
            assert "go" in t["tags"]
            assert "rest" in t["tags"]

        # Seed a task that has only "go" but not "rest" - it should NOT appear
        task_go_only = store.create_task({
            "title": "Go only task",
            "description": "Has only go tag",
            "priority": "low",
            "tags": ["go"],
        })

        resp2 = client.get("/api/v1/tasks?tags=go,rest")
        data2 = resp2.get_json()
        returned_ids = [t["id"] for t in data2["tasks"]]
        assert task_go_only.id not in returned_ids


class TestFilterCombined:
    """Combine multiple filters for correct intersection."""

    def test_filter_combined(self, client, store):
        # Seed a task with specific status and tags
        task = store.create_task({
            "title": "Combined filter test",
            "description": "Has specific status and tags",
            "priority": "high",
            "tags": ["python", "testing"],
            "assigned_to": "bob",
        })
        task.status = TaskStatus.COMPLETED

        # Seed another task that matches only one filter
        task2 = store.create_task({
            "title": "Only status match",
            "description": "Completed but different tags",
            "priority": "low",
            "tags": ["java"],
        })
        task2.status = TaskStatus.COMPLETED

        # Filter by status=completed AND tags=python,testing
        resp = client.get("/api/v1/tasks?status=completed&tags=python,testing")
        assert resp.status_code == 200

        data = resp.get_json()
        returned_ids = [t["id"] for t in data["tasks"]]
        # The task with both matching status and tags should be present
        assert task.id in returned_ids
        # The task that only matches status should NOT be present
        assert task2.id not in returned_ids

        # Also test status + assigned_to combination
        resp2 = client.get("/api/v1/tasks?status=completed&assigned_to=bob")
        data2 = resp2.get_json()
        returned_ids2 = [t["id"] for t in data2["tasks"]]
        assert task.id in returned_ids2
        assert task2.id not in returned_ids2


# =====================================================================
# GET /api/v1/tasks  — List (sorting)
# =====================================================================


class TestSortCreatedAtAsc:
    """Verify ascending sort by created_at."""

    def test_sort_created_at_asc(self, client, store):
        # Seed tasks with controlled creation times
        now = datetime.now(timezone.utc)
        task_old = store.create_task({
            "title": "Old task",
            "description": "Created first",
            "priority": "low",
        })
        task_old.created_at = now - timedelta(hours=3)

        task_mid = store.create_task({
            "title": "Mid task",
            "description": "Created second",
            "priority": "low",
        })
        task_mid.created_at = now - timedelta(hours=2)

        task_new = store.create_task({
            "title": "New task",
            "description": "Created third",
            "priority": "low",
        })
        task_new.created_at = now - timedelta(hours=1)

        resp = client.get("/api/v1/tasks?sort_order=created_at_asc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]
        # Verify ascending order: each task's created_at <= next task's created_at
        for i in range(len(tasks) - 1):
            assert tasks[i]["created_at"] <= tasks[i + 1]["created_at"]


class TestSortCreatedAtDesc:
    """Verify descending sort by created_at."""

    def test_sort_created_at_desc(self, client, store):
        now = datetime.now(timezone.utc)
        task_old = store.create_task({
            "title": "Old task desc",
            "description": "Created first",
            "priority": "low",
        })
        task_old.created_at = now - timedelta(hours=3)

        task_new = store.create_task({
            "title": "New task desc",
            "description": "Created last",
            "priority": "low",
        })
        task_new.created_at = now - timedelta(hours=1)

        resp = client.get("/api/v1/tasks?sort_order=created_at_desc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]
        # Verify descending order: each task's created_at >= next task's created_at
        for i in range(len(tasks) - 1):
            assert tasks[i]["created_at"] >= tasks[i + 1]["created_at"]


class TestSortDueDateAsc:
    """Ascending sort with nil-last for due_date."""

    def test_sort_due_date_asc(self, client, store):
        now = datetime.now(timezone.utc)

        task_no_due = store.create_task({
            "title": "No due date",
            "description": "Should be at end",
            "priority": "low",
        })
        # due_date is None by default

        task_later = store.create_task({
            "title": "Later due",
            "description": "Due later",
            "priority": "low",
            "due_date": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        task_sooner = store.create_task({
            "title": "Sooner due",
            "description": "Due sooner",
            "priority": "low",
            "due_date": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        resp = client.get("/api/v1/tasks?sort_order=due_date_asc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]

        # Separate tasks with and without due dates
        with_due = [t for t in tasks if "due_date" in t]
        without_due = [t for t in tasks if "due_date" not in t]

        # Tasks without due_date should appear at the end (nil-last)
        if with_due and without_due:
            last_with_due_idx = max(
                i for i, t in enumerate(tasks) if "due_date" in t
            )
            first_without_due_idx = min(
                i for i, t in enumerate(tasks) if "due_date" not in t
            )
            assert last_with_due_idx < first_without_due_idx

        # Tasks with due dates should be in ascending order
        for i in range(len(with_due) - 1):
            assert with_due[i]["due_date"] <= with_due[i + 1]["due_date"]


class TestSortDueDateDesc:
    """Descending sort with nil-last for due_date."""

    def test_sort_due_date_desc(self, client, store):
        now = datetime.now(timezone.utc)

        task_no_due = store.create_task({
            "title": "No due date desc",
            "description": "Should be at end",
            "priority": "low",
        })

        task_later = store.create_task({
            "title": "Later due desc",
            "description": "Due later",
            "priority": "low",
            "due_date": (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        task_sooner = store.create_task({
            "title": "Sooner due desc",
            "description": "Due sooner",
            "priority": "low",
            "due_date": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        resp = client.get("/api/v1/tasks?sort_order=due_date_desc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]

        with_due = [t for t in tasks if "due_date" in t]
        without_due = [t for t in tasks if "due_date" not in t]

        # Tasks without due_date should still appear at the end (nil-last)
        if with_due and without_due:
            last_with_due_idx = max(
                i for i, t in enumerate(tasks) if "due_date" in t
            )
            first_without_due_idx = min(
                i for i, t in enumerate(tasks) if "due_date" not in t
            )
            assert last_with_due_idx < first_without_due_idx

        # Tasks with due dates should be in descending order
        for i in range(len(with_due) - 1):
            assert with_due[i]["due_date"] >= with_due[i + 1]["due_date"]


class TestSortPriorityAsc:
    """Ascending sort by numeric priority value."""

    def test_sort_priority_asc(self, client, store):
        store.create_task({
            "title": "Critical task",
            "description": "Prio critical",
            "priority": "critical",
        })
        store.create_task({
            "title": "Low task",
            "description": "Prio low",
            "priority": "low",
        })
        store.create_task({
            "title": "High task",
            "description": "Prio high",
            "priority": "high",
        })
        store.create_task({
            "title": "Medium task",
            "description": "Prio medium",
            "priority": "medium",
        })

        resp = client.get("/api/v1/tasks?sort_order=priority_asc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]

        priority_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        for i in range(len(tasks) - 1):
            assert priority_order[tasks[i]["priority"]] <= priority_order[tasks[i + 1]["priority"]]


class TestSortPriorityDesc:
    """Descending sort by numeric priority value."""

    def test_sort_priority_desc(self, client, store):
        store.create_task({
            "title": "Critical task desc",
            "description": "Prio critical",
            "priority": "critical",
        })
        store.create_task({
            "title": "Low task desc",
            "description": "Prio low",
            "priority": "low",
        })
        store.create_task({
            "title": "High task desc",
            "description": "Prio high",
            "priority": "high",
        })
        store.create_task({
            "title": "Medium task desc",
            "description": "Prio medium",
            "priority": "medium",
        })

        resp = client.get("/api/v1/tasks?sort_order=priority_desc")
        assert resp.status_code == 200

        data = resp.get_json()
        tasks = data["tasks"]

        priority_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        for i in range(len(tasks) - 1):
            assert priority_order[tasks[i]["priority"]] >= priority_order[tasks[i + 1]["priority"]]


# =====================================================================
# GET /api/v1/tasks/<id>  — Get by ID
# =====================================================================


class TestGetTaskValidId:
    """Get a seeded task by ID returns all expected fields."""

    def test_get_task_valid_id(self, client, store):
        # Use a seeded task - grab the first one from the store
        task_id = next(iter(store._tasks))
        task = store._tasks[task_id]

        resp = client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200

        data = resp.get_json()
        # Verify all expected fields are present
        assert data["id"] == task_id
        assert data["title"] == task.title
        assert data["description"] == task.description
        assert data["status"] == task.status.value
        assert data["priority"] == task.priority.value
        assert data["tags"] == task.tags
        assert data["created_by"] == task.created_by
        assert "created_at" in data
        assert "updated_at" in data


class TestGetTaskNotFound:
    """Requesting nonexistent ID returns 404 with NOT_FOUND."""

    def test_get_task_not_found(self, client):
        resp = client.get("/api/v1/tasks/nonexistent-uuid")
        assert resp.status_code == 404

        data = resp.get_json()
        assert data["error"]["code"] == "NOT_FOUND"
