"""Functional tests for task-management-api write endpoints.

Tests cover:
- POST /api/v1/tasks (create)
- PUT /api/v1/tasks/<id> (update)
- PATCH /api/v1/tasks/<id>/status (update status)
- DELETE /api/v1/tasks/<id> (delete)

All entities are origin_and_target: origin is the Go/Gin baseline,
target is the Python/Flask port.
"""

import json
import os
import re

import pytest
import requests

BASE_URL = f"http://localhost:{os.environ.get('PORT', '8080')}"
RESULTS_FILE = os.environ.get("FT_RESULTS_FILE", "/tmp/ft_results.json")


@pytest.fixture(autouse=True)
def health_check():
    """Confirm the app is reachable before running tests.

    Since only write endpoints exist in the target milestone, we POST
    a task as a reachability probe.  For origin (Go), GET /health is
    available -- but POST /api/v1/tasks works for both.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v1/tasks",
            json={"title": "healthcheck-probe"},
            timeout=5,
        )
        assert resp.status_code == 201, f"Health probe failed: {resp.status_code}"
    except requests.ConnectionError:
        pytest.fail("Server is not reachable -- is it running?")


def _create_task(payload=None):
    """Helper: create a task and return (response, body)."""
    if payload is None:
        payload = {"title": "Test task", "description": "desc", "priority": "high"}
    resp = requests.post(f"{BASE_URL}/api/v1/tasks", json=payload, timeout=10)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp, body


# ====================================================================
# POST /api/v1/tasks
# ====================================================================

class TestCreateTask:
    """POST /api/v1/tasks -- happy path and error cases."""

    def test_create_task_success(self):
        """HAPPY_PATH: Create a valid task and verify 201 + Location header."""
        payload = {
            "title": "Buy groceries",
            "description": "Milk, eggs, bread",
            "priority": "high",
            "tags": ["shopping", "personal"],
        }
        resp, body = _create_task(payload)
        assert resp.status_code == 201
        assert "Location" in resp.headers
        assert body["title"] == "Buy groceries"
        assert body["description"] == "Milk, eggs, bread"
        assert body["priority"] == "high"
        assert body["status"] == "pending"
        assert body["tags"] == ["shopping", "personal"]
        assert body["created_by"] == "system"
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        # omitempty: assigned_to, due_date, completed_at should be absent
        assert "assigned_to" not in body
        assert "due_date" not in body
        assert "completed_at" not in body
        # Location header points to the task
        assert resp.headers["Location"] == f"/api/v1/tasks/{body['id']}"
        # Timestamps use RFC3339 with Z suffix
        assert body["created_at"].endswith("Z")
        assert body["updated_at"].endswith("Z")

    def test_create_task_default_priority(self):
        """HAPPY_PATH: Omitting priority defaults to 'medium'."""
        payload = {"title": "No priority task"}
        resp, body = _create_task(payload)
        assert resp.status_code == 201
        assert body["priority"] == "medium"

    def test_create_task_default_tags(self):
        """HAPPY_PATH: Omitting tags defaults to empty list."""
        payload = {"title": "No tags task"}
        resp, body = _create_task(payload)
        assert resp.status_code == 201
        assert body["tags"] == [] or body["tags"] is None or body.get("tags") == []

    def test_create_task_with_assigned_to(self):
        """HAPPY_PATH: Providing assigned_to includes it in response."""
        payload = {"title": "Assigned task", "assigned_to": "alice"}
        resp, body = _create_task(payload)
        assert resp.status_code == 201
        assert body["assigned_to"] == "alice"

    def test_create_task_with_due_date(self):
        """HAPPY_PATH: Providing due_date includes it in response."""
        payload = {"title": "Due date task", "due_date": "2025-12-31T00:00:00Z"}
        resp, body = _create_task(payload)
        assert resp.status_code == 201
        assert "due_date" in body

    def test_create_task_missing_title(self):
        """MISSING_REQUIRED: No title -> 400 VALIDATION_ERROR."""
        payload = {"description": "No title here"}
        resp = requests.post(f"{BASE_URL}/api/v1/tasks", json=payload, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_create_task_empty_title(self):
        """MISSING_REQUIRED: Empty string title -> 400."""
        payload = {"title": ""}
        resp = requests.post(f"{BASE_URL}/api/v1/tasks", json=payload, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_create_task_invalid_priority(self):
        """INVALID_INPUT: Invalid priority -> 400 VALIDATION_ERROR."""
        payload = {"title": "Bad priority", "priority": "urgent"}
        resp = requests.post(f"{BASE_URL}/api/v1/tasks", json=payload, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_create_task_title_too_long(self):
        """BOUNDARY: Title > 200 chars -> 400."""
        payload = {"title": "A" * 201}
        resp = requests.post(f"{BASE_URL}/api/v1/tasks", json=payload, timeout=10)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_create_task_no_json_body(self):
        """INVALID_FORMAT: Non-JSON body -> 400."""
        resp = requests.post(
            f"{BASE_URL}/api/v1/tasks",
            data="not json",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        assert resp.status_code == 400


# ====================================================================
# PUT /api/v1/tasks/<id>
# ====================================================================

class TestUpdateTask:
    """PUT /api/v1/tasks/<id> -- partial update tests."""

    def test_update_task_partial(self):
        """HAPPY_PATH: Only provided fields change."""
        resp, created = _create_task({"title": "Original", "priority": "low"})
        task_id = created["id"]

        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            json={"title": "Updated"},
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Updated"
        assert body["priority"] == "low"  # unchanged

    def test_update_task_set_completed(self):
        """HAPPY_PATH: Setting status to 'completed' adds completed_at."""
        resp, created = _create_task({"title": "To complete"})
        task_id = created["id"]

        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            json={"status": "completed"},
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert "completed_at" in body
        assert body["completed_at"].endswith("Z")

    def test_update_task_invalid_status(self):
        """INVALID_INPUT: Invalid status -> 400."""
        resp, created = _create_task({"title": "Bad status"})
        task_id = created["id"]

        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            json={"status": "bogus"},
            timeout=10,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_update_task_invalid_priority(self):
        """INVALID_INPUT: Invalid priority -> 400."""
        resp, created = _create_task({"title": "Bad prio"})
        task_id = created["id"]

        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            json={"priority": "super-high"},
            timeout=10,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_update_task_not_found(self):
        """NOT_FOUND: Unknown ID -> 404."""
        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/00000000-0000-0000-0000-000000000000",
            json={"title": "Ghost"},
            timeout=10,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"


# ====================================================================
# PATCH /api/v1/tasks/<id>/status
# ====================================================================

class TestUpdateTaskStatus:
    """PATCH /api/v1/tasks/<id>/status -- status-only updates."""

    def test_update_status_success(self):
        """HAPPY_PATH: Valid status transition -> 200."""
        resp, created = _create_task({"title": "Status test"})
        task_id = created["id"]

        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/{task_id}/status",
            json={"status": "in_progress"},
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "in_progress"

    def test_update_status_completed(self):
        """HAPPY_PATH: Setting to 'completed' adds completed_at."""
        resp, created = _create_task({"title": "Complete me"})
        task_id = created["id"]

        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/{task_id}/status",
            json={"status": "completed"},
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert "completed_at" in body

    def test_update_status_invalid(self):
        """INVALID_INPUT: Invalid status -> 400."""
        resp, created = _create_task({"title": "Bad status"})
        task_id = created["id"]

        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/{task_id}/status",
            json={"status": "invalid_status"},
            timeout=10,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_update_status_not_found(self):
        """NOT_FOUND: Unknown ID -> 404."""
        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/00000000-0000-0000-0000-000000000000/status",
            json={"status": "pending"},
            timeout=10,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"

    def test_update_status_missing_status_field(self):
        """MISSING_REQUIRED: No status field -> 400."""
        resp, created = _create_task({"title": "Missing status"})
        task_id = created["id"]

        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/{task_id}/status",
            json={},
            timeout=10,
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"


# ====================================================================
# DELETE /api/v1/tasks/<id>
# ====================================================================

class TestDeleteTask:
    """DELETE /api/v1/tasks/<id> -- deletion tests."""

    def test_delete_task_success(self):
        """HAPPY_PATH: Valid ID -> 204 empty body."""
        resp, created = _create_task({"title": "Delete me"})
        task_id = created["id"]

        resp = requests.delete(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        assert resp.status_code == 204
        assert resp.text == "" or resp.content == b""

    def test_delete_task_not_found(self):
        """NOT_FOUND: Unknown ID -> 404."""
        resp = requests.delete(
            f"{BASE_URL}/api/v1/tasks/00000000-0000-0000-0000-000000000000",
            timeout=10,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"

    def test_delete_task_subsequent_operations_404(self):
        """HAPPY_PATH: After deleting, PUT on same ID -> 404."""
        resp, created = _create_task({"title": "Will be deleted"})
        task_id = created["id"]

        # Delete
        resp = requests.delete(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        assert resp.status_code == 204

        # Subsequent PUT should be 404
        resp = requests.put(
            f"{BASE_URL}/api/v1/tasks/{task_id}",
            json={"title": "Ghost update"},
            timeout=10,
        )
        assert resp.status_code == 404

    def test_delete_task_subsequent_patch_404(self):
        """HAPPY_PATH: After deleting, PATCH status on same ID -> 404."""
        resp, created = _create_task({"title": "Will be deleted too"})
        task_id = created["id"]

        # Delete
        resp = requests.delete(f"{BASE_URL}/api/v1/tasks/{task_id}", timeout=10)
        assert resp.status_code == 204

        # Subsequent PATCH should be 404
        resp = requests.patch(
            f"{BASE_URL}/api/v1/tasks/{task_id}/status",
            json={"status": "completed"},
            timeout=10,
        )
        assert resp.status_code == 404
