using Microsoft.AspNetCore.Mvc;
using TaskManagementApi.Models;
using TaskManagementApi.Models.Requests;
using TaskManagementApi.Models.Responses;
using TaskManagementApi.Services;

namespace TaskManagementApi.Controllers;

/// <summary>
/// REST API controller for task management operations.
/// Maps 1:1 to Go's Gin handler functions in rest/server/handlers.go.
/// </summary>
[ApiController]
[Route("api/v1/tasks")]
public class TasksController : ControllerBase
{
    private readonly TaskService _taskService;

    public TasksController(TaskService taskService)
    {
        _taskService = taskService;
    }

    /// <summary>
    /// GET /api/v1/tasks — Lists tasks with filtering, sorting, and pagination.
    /// Mirrors Go's listTasks handler.
    /// </summary>
    [HttpGet]
    public IActionResult ListTasks([FromQuery] ListTasksQuery query)
    {
        // Set default page size if not provided (matches Go: if query.PageSize == 0 { query.PageSize = 20 })
        if (query.PageSize == 0)
        {
            query.PageSize = 20;
        }

        var response = _taskService.ListTasks(query);
        return Ok(response);
    }

    /// <summary>
    /// GET /api/v1/tasks/{id} — Retrieves a single task by ID.
    /// Mirrors Go's getTask handler. NotFoundException propagates to middleware → 404.
    /// </summary>
    [HttpGet("{id}")]
    public IActionResult GetTask(string id)
    {
        var task = _taskService.GetTask(id);
        return Ok(task);
    }

    /// <summary>
    /// POST /api/v1/tasks — Creates a new task.
    /// Mirrors Go's createTask handler. Returns 201 with Location header.
    /// ValidationException propagates to middleware → 400.
    /// </summary>
    [HttpPost]
    public IActionResult CreateTask([FromBody] CreateTaskRequest request)
    {
        var task = _taskService.CreateTask(request);

        // Set Location header matching Go: "/api/v1/tasks/{id}"
        Response.Headers["Location"] = $"/api/v1/tasks/{task.Id}";

        return StatusCode(StatusCodes.Status201Created, task);
    }

    /// <summary>
    /// PUT /api/v1/tasks/{id} — Updates an existing task (partial update with optional fields).
    /// Mirrors Go's updateTask handler.
    /// NotFoundException → 404, ValidationException → 400 via middleware.
    /// </summary>
    [HttpPut("{id}")]
    public IActionResult UpdateTask(string id, [FromBody] UpdateTaskRequest request)
    {
        var task = _taskService.UpdateTask(id, request);
        return Ok(task);
    }

    /// <summary>
    /// PATCH /api/v1/tasks/{id}/status — Updates only the task's status.
    /// Mirrors Go's updateTaskStatus handler.
    /// Validates status IsValid() before calling service (matching Go's inline validation).
    /// </summary>
    [HttpPatch("{id}/status")]
    public IActionResult UpdateTaskStatus(string id, [FromBody] UpdateTaskStatusRequest request)
    {
        // Validate that the status value is a valid enum member
        // This mirrors Go's explicit check: if !req.Status.IsValid() { ... }
        if (request.Status == null || !request.Status.Value.IsValid())
        {
            var statusValue = request.Status?.ToSnakeCase() ?? "null";
            throw new ValidationException($"invalid status: {statusValue}");
        }

        var task = _taskService.UpdateTaskStatus(id, request.Status.Value);
        return Ok(task);
    }

    /// <summary>
    /// DELETE /api/v1/tasks/{id} — Deletes a task.
    /// Mirrors Go's deleteTask handler. Returns 204 No Content on success.
    /// NotFoundException propagates to middleware → 404.
    /// </summary>
    [HttpDelete("{id}")]
    public IActionResult DeleteTask(string id)
    {
        _taskService.DeleteTask(id);
        return NoContent();
    }
}
