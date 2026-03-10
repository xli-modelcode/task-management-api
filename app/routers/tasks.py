"""
Task HTTP handlers / routes.

Translated from rest/server/handlers.go (partial – createTask, getTask,
deleteTask for Milestone 1).
"""

from fastapi import APIRouter, FastAPI, Response
from fastapi.responses import JSONResponse

from app.models.task import CreateTaskRequest, Task
from app.services.task_service import TaskService

# Module-level reference injected by ``register()``.
_service: TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def register(app: FastAPI, service: TaskService) -> None:
    """Wire the shared TaskService and mount the router on *app*."""
    global _service  # noqa: PLW0603
    _service = service
    app.include_router(router)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Return a JSON error matching the Go API contract."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _task_dict(task: Task) -> dict:
    """Serialise a Task to a dict, excluding None fields (Go omitempty)."""
    return task.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_task(req: CreateTaskRequest) -> JSONResponse:
    """POST /api/v1/tasks – create a new task."""
    try:
        task = _service.create_task(req)
    except ValueError as exc:
        return _error_response(400, "VALIDATION_ERROR", str(exc))

    return JSONResponse(
        status_code=201,
        content=_task_dict(task),
        headers={"Location": f"/api/v1/tasks/{task.id}"},
    )


@router.get("/{task_id}")
async def get_task(task_id: str) -> JSONResponse:
    """GET /api/v1/tasks/{id} – retrieve a single task."""
    try:
        task = _service.get_task(task_id)
    except ValueError as exc:
        return _error_response(404, "NOT_FOUND", str(exc))

    return JSONResponse(status_code=200, content=_task_dict(task))


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, response: Response) -> Response:
    """DELETE /api/v1/tasks/{id} – delete a task."""
    try:
        _service.delete_task(task_id)
    except ValueError as exc:
        return _error_response(404, "NOT_FOUND", str(exc))

    response.status_code = 204
    return response
