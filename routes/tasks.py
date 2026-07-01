"""Task write endpoints ported from Go rest/server/handlers.go."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from models import (
    TaskNotFoundError,
    TaskStatus,
    TaskPriority,
    ValidationError,
    error_response,
)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")


def _get_store():
    """Return the ``TaskStore`` attached to the running app."""
    return current_app.config["TASK_STORE"]


# ------------------------------------------------------------------
# POST /api/v1/tasks
# ------------------------------------------------------------------

@tasks_bp.route("", methods=["POST"])
def create_task():
    """Create a new task.

    Mirrors Go ``createTask`` handler: validates title (required,
    1-200 chars), delegates to store, returns 201 + Location header.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error_response("VALIDATION_ERROR", "request body must be JSON")), 400

    title = data.get("title")

    # Title is required, 1-200 chars (matches Gin ``binding:"required,min=1,max=200"``)
    if title is None or not isinstance(title, str) or len(title.strip()) == 0:
        return jsonify(error_response("VALIDATION_ERROR", "title is required")), 400
    if len(title) > 200:
        return jsonify(error_response("VALIDATION_ERROR", "title must be between 1 and 200 characters")), 400

    store = _get_store()

    try:
        task = store.create_task(data)
    except ValidationError as exc:
        return jsonify(error_response("VALIDATION_ERROR", str(exc))), 400

    response = jsonify(task.to_dict())
    response.status_code = 201
    response.headers["Location"] = f"/api/v1/tasks/{task.id}"
    return response


# ------------------------------------------------------------------
# PUT /api/v1/tasks/<id>
# ------------------------------------------------------------------

@tasks_bp.route("/<task_id>", methods=["PUT"])
def update_task(task_id: str):
    """Full / partial update of an existing task.

    Error mapping mirrors Go ``updateTask``:
      - TaskNotFoundError -> 404 / NOT_FOUND
      - ValidationError   -> 400 / VALIDATION_ERROR
      - anything else     -> 500 / INTERNAL_ERROR
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error_response("VALIDATION_ERROR", "request body must be JSON")), 400

    store = _get_store()

    try:
        task = store.update_task(task_id, data)
    except TaskNotFoundError as exc:
        return jsonify(error_response("NOT_FOUND", str(exc))), 404
    except ValidationError as exc:
        return jsonify(error_response("VALIDATION_ERROR", str(exc))), 400
    except Exception as exc:
        return jsonify(error_response("INTERNAL_ERROR", str(exc))), 500

    return jsonify(task.to_dict()), 200


# ------------------------------------------------------------------
# PATCH /api/v1/tasks/<id>/status
# ------------------------------------------------------------------

@tasks_bp.route("/<task_id>/status", methods=["PATCH"])
def update_task_status(task_id: str):
    """Update only the task's status.

    Go validates the status enum **before** calling the service.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error_response("VALIDATION_ERROR", "request body must be JSON")), 400

    status_value = data.get("status")
    if status_value is None:
        return jsonify(error_response("VALIDATION_ERROR", "status is required")), 400

    if not TaskStatus.is_valid(status_value):
        return jsonify(error_response("VALIDATION_ERROR", f"invalid status: {status_value}")), 400

    store = _get_store()

    try:
        task = store.update_task_status(task_id, status_value)
    except TaskNotFoundError as exc:
        return jsonify(error_response("NOT_FOUND", str(exc))), 404
    except Exception as exc:
        return jsonify(error_response("INTERNAL_ERROR", str(exc))), 500

    return jsonify(task.to_dict()), 200


# ------------------------------------------------------------------
# DELETE /api/v1/tasks/<id>
# ------------------------------------------------------------------

@tasks_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id: str):
    """Delete a task — 204 on success, 404 when not found."""
    store = _get_store()

    try:
        store.delete_task(task_id)
    except TaskNotFoundError as exc:
        return jsonify(error_response("NOT_FOUND", str(exc))), 404

    return "", 204
