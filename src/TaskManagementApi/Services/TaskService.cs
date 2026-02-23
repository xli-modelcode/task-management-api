using TaskManagementApi.Models;
using TaskManagementApi.Models.Requests;
using TaskManagementApi.Models.Responses;

namespace TaskManagementApi.Services;

/// <summary>
/// Provides task management operations with in-memory storage.
/// Uses ReaderWriterLockSlim to match Go's sync.RWMutex semantics:
/// concurrent reads are allowed, writes are exclusive.
/// </summary>
public class TaskService
{
    private readonly ReaderWriterLockSlim _lock = new();
    private readonly Dictionary<string, TaskModel> _tasks = new();

    public TaskService()
    {
        InitializeSampleData();
    }

    /// <summary>
    /// Creates a new task with defaults and validation.
    /// Mirrors Go's CreateTask: generates UUID, sets status=pending,
    /// defaults priority to medium if not specified, ensures tags is non-null.
    /// </summary>
    public TaskModel CreateTask(CreateTaskRequest req)
    {
        _lock.EnterWriteLock();
        try
        {
            var now = DateTime.UtcNow;
            var priority = req.Priority ?? TaskPriority.Medium;

            // Validate priority
            if (!priority.IsValid())
            {
                throw new ValidationException($"invalid priority: {priority.ToSnakeCase()}");
            }

            var task = new TaskModel
            {
                Id = Guid.NewGuid().ToString(),
                Title = req.Title,
                Description = req.Description,
                Status = Models.TaskStatus.Pending,
                Priority = priority,
                Tags = req.Tags ?? new List<string>(),
                CreatedBy = "system",
                AssignedTo = req.AssignedTo,
                CreatedAt = now,
                UpdatedAt = now,
                DueDate = req.DueDate,
            };

            _tasks[task.Id] = task;
            return task;
        }
        finally
        {
            _lock.ExitWriteLock();
        }
    }

    /// <summary>
    /// Retrieves a task by ID. Throws NotFoundException if not found.
    /// </summary>
    public TaskModel GetTask(string id)
    {
        _lock.EnterReadLock();
        try
        {
            if (!_tasks.TryGetValue(id, out var task))
            {
                throw new NotFoundException($"task with ID {id} not found");
            }

            return task;
        }
        finally
        {
            _lock.ExitReadLock();
        }
    }

    /// <summary>
    /// Updates an existing task with partial update semantics.
    /// Only non-null fields are applied. Sets CompletedAt when status transitions to completed.
    /// Mirrors Go's UpdateTask pointer-field semantics.
    /// </summary>
    public TaskModel UpdateTask(string id, UpdateTaskRequest req)
    {
        _lock.EnterWriteLock();
        try
        {
            if (!_tasks.TryGetValue(id, out var task))
            {
                throw new NotFoundException($"task with ID {id} not found");
            }

            // Update fields if provided (null means "not provided")
            if (req.Title != null)
            {
                task.Title = req.Title;
            }

            if (req.Description != null)
            {
                task.Description = req.Description;
            }

            if (req.Status != null)
            {
                if (!req.Status.Value.IsValid())
                {
                    throw new ValidationException($"invalid status: {req.Status.Value.ToSnakeCase()}");
                }

                task.Status = req.Status.Value;

                // Set completed time if status changes to completed
                if (task.Status == Models.TaskStatus.Completed && task.CompletedAt == null)
                {
                    task.CompletedAt = DateTime.UtcNow;
                }
            }

            if (req.Priority != null)
            {
                if (!req.Priority.Value.IsValid())
                {
                    throw new ValidationException($"invalid priority: {req.Priority.Value.ToSnakeCase()}");
                }

                task.Priority = req.Priority.Value;
            }

            if (req.Tags != null)
            {
                task.Tags = req.Tags;
            }

            if (req.AssignedTo != null)
            {
                task.AssignedTo = req.AssignedTo;
            }

            if (req.DueDate != null)
            {
                task.DueDate = req.DueDate;
            }

            task.UpdatedAt = DateTime.UtcNow;
            return task;
        }
        finally
        {
            _lock.ExitWriteLock();
        }
    }

    /// <summary>
    /// Updates only the status of a task. Delegates to UpdateTask.
    /// </summary>
    public TaskModel UpdateTaskStatus(string id, Models.TaskStatus status)
    {
        return UpdateTask(id, new UpdateTaskRequest
        {
            Status = status
        });
    }

    /// <summary>
    /// Deletes a task by ID. Throws NotFoundException if not found.
    /// </summary>
    public void DeleteTask(string id)
    {
        _lock.EnterWriteLock();
        try
        {
            if (!_tasks.ContainsKey(id))
            {
                throw new NotFoundException($"task with ID {id} not found");
            }

            _tasks.Remove(id);
        }
        finally
        {
            _lock.ExitWriteLock();
        }
    }

    /// <summary>
    /// Returns a paginated, filtered, and sorted list of tasks.
    /// Mirrors Go's ListTasks with identical filtering, sorting, and pagination semantics.
    /// </summary>
    public ListTasksResponse ListTasks(ListTasksQuery query)
    {
        _lock.EnterReadLock();
        try
        {
            // Convert dictionary to list for filtering and sorting
            var tasks = new List<TaskModel>(_tasks.Values);

            // Apply filters
            tasks = FilterTasks(tasks, query);

            // Apply sorting
            SortTasks(tasks, query.SortOrder);

            // Apply pagination
            var totalCount = tasks.Count;
            var pageSize = query.PageSize;
            if (pageSize <= 0)
            {
                pageSize = 20;
            }
            if (pageSize > 100)
            {
                pageSize = 100;
            }

            var startIndex = 0;
            if (!string.IsNullOrEmpty(query.PageToken))
            {
                if (int.TryParse(query.PageToken, out var idx))
                {
                    startIndex = idx;
                }
            }

            var endIndex = startIndex + pageSize;
            if (endIndex > totalCount)
            {
                endIndex = totalCount;
            }

            var paginatedTasks = new List<TaskModel>();
            if (startIndex < totalCount)
            {
                paginatedTasks = tasks.GetRange(startIndex, endIndex - startIndex);
            }

            string? nextPageToken = null;
            if (endIndex < totalCount)
            {
                nextPageToken = endIndex.ToString();
            }

            return new ListTasksResponse
            {
                Tasks = paginatedTasks,
                NextPageToken = nextPageToken,
                TotalCount = totalCount,
            };
        }
        finally
        {
            _lock.ExitReadLock();
        }
    }

    /// <summary>
    /// Applies status, assigned_to, and tags filters to the task list.
    /// Mirrors Go's filterTasks exactly.
    /// </summary>
    private static List<TaskModel> FilterTasks(List<TaskModel> tasks, ListTasksQuery query)
    {
        var filtered = new List<TaskModel>();

        foreach (var task in tasks)
        {
            // Filter by status
            if (!string.IsNullOrEmpty(query.Status))
            {
                if (TaskStatusExtensions.TryParseSnakeCase(query.Status, out var statusFilter))
                {
                    if (task.Status != statusFilter)
                    {
                        continue;
                    }
                }
                else
                {
                    // If the status string doesn't parse, no task will match
                    continue;
                }
            }

            // Filter by assigned user
            if (!string.IsNullOrEmpty(query.AssignedTo))
            {
                if (task.AssignedTo == null || task.AssignedTo != query.AssignedTo)
                {
                    continue;
                }
            }

            // Filter by tags (AND logic - task must have ALL specified tags)
            if (!string.IsNullOrEmpty(query.Tags))
            {
                var tags = query.Tags.Split(',');
                var hasAllTags = true;
                foreach (var tag in tags)
                {
                    var trimmedTag = tag.Trim();
                    if (!task.Tags.Contains(trimmedTag))
                    {
                        hasAllTags = false;
                        break;
                    }
                }
                if (!hasAllTags)
                {
                    continue;
                }
            }

            filtered.Add(task);
        }

        return filtered;
    }

    /// <summary>
    /// Sorts tasks based on the specified sort order.
    /// Uses List.Sort (unstable) to match Go's sort.Slice behavior.
    /// Due date null handling: nulls sort last for both ascending and descending.
    /// </summary>
    private static void SortTasks(List<TaskModel> tasks, string? sortOrder)
    {
        if (string.IsNullOrEmpty(sortOrder))
        {
            return;
        }

        switch (sortOrder)
        {
            case "created_at_asc":
                tasks.Sort((a, b) => a.CreatedAt.CompareTo(b.CreatedAt));
                break;

            case "created_at_desc":
                tasks.Sort((a, b) => b.CreatedAt.CompareTo(a.CreatedAt));
                break;

            case "due_date_asc":
                tasks.Sort((a, b) =>
                {
                    if (a.DueDate == null && b.DueDate == null) return 0;
                    if (a.DueDate == null) return 1;  // null sorts last
                    if (b.DueDate == null) return -1; // null sorts last
                    return a.DueDate.Value.CompareTo(b.DueDate.Value);
                });
                break;

            case "due_date_desc":
                tasks.Sort((a, b) =>
                {
                    if (a.DueDate == null && b.DueDate == null) return 0;
                    if (a.DueDate == null) return 1;  // null sorts last
                    if (b.DueDate == null) return -1; // null sorts last
                    return b.DueDate.Value.CompareTo(a.DueDate.Value);
                });
                break;

            case "priority_asc":
                tasks.Sort((a, b) => a.Priority.GetValue().CompareTo(b.Priority.GetValue()));
                break;

            case "priority_desc":
                tasks.Sort((a, b) => b.Priority.GetValue().CompareTo(a.Priority.GetValue()));
                break;

            // Default: no sorting (matches Go behavior when sort_order is empty or unrecognized)
        }
    }

    /// <summary>
    /// Creates two sample tasks on startup, matching Go's initializeSampleData exactly.
    /// </summary>
    private void InitializeSampleData()
    {
        var sampleTasks = new List<CreateTaskRequest>
        {
            new()
            {
                Title = "Implement Go REST API",
                Description = "Create REST API with Gin framework",
                Priority = TaskPriority.High,
                Tags = new List<string> { "go", "rest", "api" },
            },
            new()
            {
                Title = "Add gRPC support",
                Description = "Implement gRPC server with native Go support",
                Priority = TaskPriority.Medium,
                Tags = new List<string> { "go", "grpc", "protobuf" },
            },
        };

        foreach (var req in sampleTasks)
        {
            CreateTask(req);
        }
    }
}
