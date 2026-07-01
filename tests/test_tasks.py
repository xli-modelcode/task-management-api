"""Tests for write endpoints: POST, PUT, PATCH, DELETE.

Each test gets a fresh app / store (via the ``client`` fixture), so
the store always starts with the two seeded sample tasks.
"""

from __future__ import annotations

import json
import uuid

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
        """After deletion, a GET (or any operation) on the same ID should 404.

        Since GET isn't implemented in this milestone yet, we use DELETE
        again — a second DELETE on the same ID must return 404.
        """
        resp, created = _create_task(client)
        task_id = created["id"]

        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 204

        # Second delete on the same ID -> 404
        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"
