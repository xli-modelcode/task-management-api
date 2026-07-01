"""Functional tests for the task management API read endpoints.

Tests cover:
  GET /health
  GET /api/v1/tasks (with pagination, filtering, sorting)
  GET /api/v1/tasks/<id>

All endpoints are origin_and_target (MODIFIED repo -- Go baseline vs Python/Flask target).
"""

import json
import os
import re

import pytest
import requests

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8080")


@pytest.fixture(autouse=True)
def health_check():
    """Confirm the app is reachable before running tests."""
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200


# -------------------------------------------------------------------------
# GET /health
# -------------------------------------------------------------------------

class TestHealthEndpoint:
    """GET /health -- happy path and structure checks."""

    def test_health_returns_200(self):
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_health_json_structure(self):
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "task-api-go"
        assert body["version"] == "1.0.0"
        assert "timestamp" in body

    def test_health_timestamp_format(self):
        """Timestamp should be valid RFC3339 format."""
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        body = resp.json()
        ts = body["timestamp"]
        # Accept both Z suffix and timezone offset (origin uses offset, target uses Z)
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$"
        assert re.match(pattern, ts), f"Timestamp '{ts}' does not match RFC3339 format"

    def test_health_cors_header(self):
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


# -------------------------------------------------------------------------
# GET /api/v1/tasks -- List tasks
# -------------------------------------------------------------------------

class TestListTasksHappyPath:
    """GET /api/v1/tasks -- default listing and response structure."""

    def test_list_tasks_returns_200(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        assert resp.status_code == 200

    def test_list_tasks_structure(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        body = resp.json()
        assert "tasks" in body
        assert "total_count" in body
        assert isinstance(body["total_count"], int)

    def test_list_tasks_returns_seeded_data(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        body = resp.json()
        assert body["total_count"] >= 2
        titles = [t["title"] for t in body["tasks"]]
        assert "Implement Go REST API" in titles
        assert "Add gRPC support" in titles

    def test_list_tasks_task_structure(self):
        """Verify that each task in the list has the expected fields."""
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        body = resp.json()
        for task in body["tasks"]:
            assert "id" in task
            assert "title" in task
            assert "description" in task
            assert "status" in task
            assert "priority" in task
            assert "tags" in task
            assert "created_by" in task
            assert "created_at" in task
            assert "updated_at" in task

    def test_list_tasks_omitempty_fields(self):
        """Verify optional fields are omitted when None (omitempty behavior)."""
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        body = resp.json()
        for task in body["tasks"]:
            # Seeded tasks have no assigned_to, due_date, or completed_at
            assert "assigned_to" not in task, "assigned_to should be omitted when None"
            assert "due_date" not in task, "due_date should be omitted when None"
            assert "completed_at" not in task, "completed_at should be omitted when None"

    def test_list_tasks_cors_header(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


class TestListTasksPagination:
    """GET /api/v1/tasks -- pagination with page_size and page_token."""

    def test_page_size_limits_results(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": 1}, timeout=10)
        body = resp.json()
        assert resp.status_code == 200
        assert len(body["tasks"]) == 1
        assert body["total_count"] >= 2

    def test_page_size_1_has_next_page_token(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": 1}, timeout=10)
        body = resp.json()
        assert "next_page_token" in body
        assert body["next_page_token"] != ""

    def test_follow_page_token(self):
        """page_size=1 then follow next_page_token to get the second task."""
        resp1 = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": 1}, timeout=10)
        body1 = resp1.json()
        token = body1.get("next_page_token", "")
        assert token != "", "Expected a next_page_token"

        resp2 = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"page_size": 1, "page_token": token},
            timeout=10,
        )
        body2 = resp2.json()
        assert resp2.status_code == 200
        assert len(body2["tasks"]) >= 1
        # The two pages should return different tasks
        assert body1["tasks"][0]["id"] != body2["tasks"][0]["id"]

    def test_last_page_no_next_token(self):
        """When page_size is large enough to contain all, no next_page_token."""
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": 100}, timeout=10)
        body = resp.json()
        assert "next_page_token" not in body

    def test_default_page_size(self):
        """Without page_size, default is 20 -- should return all seeded tasks."""
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        body = resp.json()
        assert len(body["tasks"]) == body["total_count"]


class TestListTasksInvalidInput:
    """GET /api/v1/tasks -- invalid inputs for page_size."""

    def test_invalid_page_size_string(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": "abc"}, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_page_size_float(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": "1.5"}, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_negative_page_size(self):
        """Negative page_size -- Go returns 400 via binding validation."""
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"page_size": -1}, timeout=10)
        assert resp.status_code == 400


class TestListTasksFiltering:
    """GET /api/v1/tasks -- filtering by status, assigned_to, tags."""

    def test_filter_by_status_pending(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"status": "pending"}, timeout=10)
        body = resp.json()
        assert resp.status_code == 200
        for task in body["tasks"]:
            assert task["status"] == "pending"

    def test_filter_by_status_no_match(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"status": "completed"}, timeout=10)
        body = resp.json()
        assert resp.status_code == 200
        assert body["total_count"] == 0
        # Go returns null for empty slice, Python returns []
        tasks = body.get("tasks")
        assert tasks is None or len(tasks) == 0

    def test_filter_by_assigned_to_no_match(self):
        """No seeded tasks have assigned_to set, so filtering should return empty."""
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"assigned_to": "nonexistent-user"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body["total_count"] == 0

    def test_filter_by_single_tag(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"tags": "go"}, timeout=10)
        body = resp.json()
        assert resp.status_code == 200
        assert body["total_count"] == 2  # Both seeded tasks have "go" tag
        for task in body["tasks"]:
            assert "go" in task["tags"]

    def test_filter_by_multiple_tags_and_logic(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks", params={"tags": "go,rest"}, timeout=10)
        body = resp.json()
        assert resp.status_code == 200
        assert body["total_count"] == 1  # Only "Implement Go REST API" has both
        for task in body["tasks"]:
            assert "go" in task["tags"]
            assert "rest" in task["tags"]

    def test_filter_by_nonexistent_tag(self):
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"tags": "nonexistent-tag"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body["total_count"] == 0


class TestListTasksSorting:
    """GET /api/v1/tasks -- sorting by various fields."""

    def test_sort_created_at_asc(self):
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "created_at_asc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        if len(tasks) >= 2:
            assert tasks[0]["created_at"] <= tasks[1]["created_at"]

    def test_sort_created_at_desc(self):
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "created_at_desc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        if len(tasks) >= 2:
            assert tasks[0]["created_at"] >= tasks[1]["created_at"]

    def test_sort_priority_asc(self):
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "priority_asc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        if len(tasks) >= 2:
            priority_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            assert priority_order[tasks[0]["priority"]] <= priority_order[tasks[1]["priority"]]

    def test_sort_priority_desc(self):
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "priority_desc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        if len(tasks) >= 2:
            priority_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            assert priority_order[tasks[0]["priority"]] >= priority_order[tasks[1]["priority"]]

    def test_sort_due_date_asc_nil_last(self):
        """Tasks without due_date should sort AFTER tasks with due_date in asc order."""
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "due_date_asc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        assert len(tasks) >= 2

    def test_sort_due_date_desc_nil_last(self):
        """Tasks without due_date should sort AFTER tasks with due_date in desc order."""
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks",
            params={"sort_order": "due_date_desc"},
            timeout=10,
        )
        body = resp.json()
        assert resp.status_code == 200
        tasks = body["tasks"]
        assert len(tasks) >= 2


# -------------------------------------------------------------------------
# GET /api/v1/tasks/<id>
# -------------------------------------------------------------------------

class TestGetTaskHappyPath:
    """GET /api/v1/tasks/:id -- happy path."""

    def test_get_task_by_valid_id(self):
        # First, list tasks to get a valid ID
        list_resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        tasks = list_resp.json()["tasks"]
        assert len(tasks) > 0
        task_id = tasks[0]["id"]

        resp = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == task_id
        assert "title" in body
        assert "description" in body
        assert "status" in body
        assert "priority" in body
        assert "tags" in body

    def test_get_task_full_structure(self):
        """Verify the complete task JSON structure matches expectations."""
        list_resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        tasks = list_resp.json()["tasks"]
        task_id = tasks[0]["id"]

        resp = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        body = resp.json()
        assert body["created_by"] == "system"
        assert "created_at" in body
        assert "updated_at" in body
        # Verify timestamp is RFC3339 (Z or offset)
        ts = body["created_at"]
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        assert re.match(pattern, ts), f"created_at '{ts}' is not RFC3339"

    def test_get_task_cors_header(self):
        list_resp = requests.get(f"{BASE_URL}/api/v1/tasks", timeout=10)
        task_id = list_resp.json()["tasks"][0]["id"]
        resp = requests.get(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"


class TestGetTaskNotFound:
    """GET /api/v1/tasks/:id -- not found cases."""

    def test_get_task_invalid_id_404(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks/nonexistent-id-12345", timeout=10)
        assert resp.status_code == 404

    def test_get_task_404_error_structure(self):
        resp = requests.get(f"{BASE_URL}/api/v1/tasks/nonexistent-id-12345", timeout=10)
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "NOT_FOUND"
        assert "message" in body["error"]

    def test_get_task_empty_id_pattern(self):
        """UUID-like but nonexistent ID should return 404."""
        resp = requests.get(
            f"{BASE_URL}/api/v1/tasks/00000000-0000-0000-0000-000000000000",
            timeout=10,
        )
        assert resp.status_code == 404
