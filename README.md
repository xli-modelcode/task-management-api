# Task Management REST API - Python Implementation

A task management REST API built with Python and FastAPI. This implementation provides CRUD operations for tasks with support for pagination, filtering, and status management. Translated from the original Go/Gin implementation.

## Directory Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, health endpoint, settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py          # Pydantic models and enums
│   ├── services/
│   │   ├── __init__.py
│   │   └── task_service.py  # In-memory store and business logic
│   └── routers/
│       ├── __init__.py
│       └── tasks.py         # HTTP route handlers
├── tests/
│   ├── __init__.py
│   └── test_tasks.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.12 or higher

## Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Server

```bash
# Run with uvicorn (development with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Or run via Python
python -m app.main
```

**Configuration:**

The server reads configuration from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT`   | `8080`  | Server port |
| `HOST`   | `0.0.0.0` | Server host |
| `DEBUG`  | `true`  | Debug mode |

```bash
# Run on custom port
PORT=3000 uvicorn app.main:app --host 0.0.0.0 --port 3000
```

## API Documentation

- Swagger UI: `http://localhost:8080/docs`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## API Endpoints

### Health Check
- `GET /health` - Server health status

### Tasks
- `GET /api/v1/tasks` - List all tasks
  - Query params: `page_size`, `page_token`, `status`, `assigned_to`, `tags`, `sort_order`
- `GET /api/v1/tasks/{id}` - Get a specific task
- `POST /api/v1/tasks` - Create a new task
- `PUT /api/v1/tasks/{id}` - Update a task
- `PATCH /api/v1/tasks/{id}/status` - Update task status only
- `DELETE /api/v1/tasks/{id}` - Delete a task

## Task Model

### Task Statuses
- `pending` - Task is pending
- `in_progress` - Task is being worked on
- `completed` - Task is completed
- `cancelled` - Task is cancelled
- `on_hold` - Task is on hold

### Task Priorities
- `low` - Low priority
- `medium` - Medium priority (default)
- `high` - High priority
- `critical` - Critical priority

### Task Fields
```json
{
  "id": "uuid",
  "title": "string (required, 1-200 chars)",
  "description": "string",
  "status": "TaskStatus",
  "priority": "TaskPriority",
  "tags": ["string"],
  "created_by": "string",
  "assigned_to": "string (optional)",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "due_date": "timestamp (optional)",
  "completed_at": "timestamp (optional)"
}
```

## Example Usage

### Create a Task
```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn Python",
    "description": "Complete the FastAPI tutorial",
    "priority": "high",
    "tags": ["learning", "python"]
  }'
```

### List Tasks
```bash
# All tasks
curl http://localhost:8080/api/v1/tasks

# Filtered by status
curl http://localhost:8080/api/v1/tasks?status=pending

# With pagination
curl http://localhost:8080/api/v1/tasks?page_size=10&sort_order=priority_desc
```

### Get a Task
```bash
curl http://localhost:8080/api/v1/tasks/{id}
```

### Update Task Status
```bash
curl -X PATCH http://localhost:8080/api/v1/tasks/{id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
```

### Delete a Task
```bash
curl -X DELETE http://localhost:8080/api/v1/tasks/{id}
```

## Running Tests

```bash
pytest

# With coverage
pytest --cov=app --cov-report=term-missing
```

## Features

- **FastAPI Framework** - Modern async Python web framework with automatic OpenAPI docs
- **In-memory Storage** - Task data stored in memory (no database required)
- **Pydantic Validation** - Request validation with Pydantic v2 models
- **Error Handling** - Consistent error responses matching the Go API contract
- **CORS Support** - Cross-origin resource sharing enabled
- **Pagination** - Page-based pagination with tokens
- **Filtering & Sorting** - Query by status, assignee, tags; sort by various fields
- **UUID-based IDs** - Unique identifiers for all tasks

## HTTP Status Codes

- `200 OK` - Successful GET/PUT/PATCH request
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Validation error or invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message"
  }
}
```

Common error codes:
- `VALIDATION_ERROR` - Invalid input data
- `NOT_FOUND` - Resource not found
- `INTERNAL_ERROR` - Server error
