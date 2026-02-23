using System.Collections.Concurrent;
using TaskManagementApi.Models;
using TaskManagementApi.Models.Requests;
using TaskManagementApi.Models.Responses;

namespace TaskManagementApi.Services;

/// <summary>
/// Provides task management operations with in-memory storage.
/// Stub implementation — full logic will be added in Milestone 2.
/// </summary>
public class TaskService
{
    private readonly ConcurrentDictionary<string, TaskModel> _tasks = new();

    public TaskService()
    {
        // Sample data initialization will be added in Milestone 2
    }
}
