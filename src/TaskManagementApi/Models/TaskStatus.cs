namespace TaskManagementApi.Models;

/// <summary>
/// Represents the current state of a task.
/// Global JsonStringEnumConverter with SnakeCaseLower in Program.cs handles serialization.
/// </summary>
public enum TaskStatus
{
    Pending,
    InProgress,
    Completed,
    Cancelled,
    OnHold
}

public static class TaskStatusExtensions
{
    /// <summary>
    /// Validates whether the given TaskStatus value is a defined enum member.
    /// </summary>
    public static bool IsValid(this TaskStatus status)
    {
        return status is TaskStatus.Pending
            or TaskStatus.InProgress
            or TaskStatus.Completed
            or TaskStatus.Cancelled
            or TaskStatus.OnHold;
    }

    /// <summary>
    /// Tries to parse a string into a TaskStatus value using snake_case convention.
    /// </summary>
    public static bool TryParseSnakeCase(string? value, out TaskStatus result)
    {
        result = default;
        if (string.IsNullOrEmpty(value))
            return false;

        switch (value)
        {
            case "pending":
                result = TaskStatus.Pending;
                return true;
            case "in_progress":
                result = TaskStatus.InProgress;
                return true;
            case "completed":
                result = TaskStatus.Completed;
                return true;
            case "cancelled":
                result = TaskStatus.Cancelled;
                return true;
            case "on_hold":
                result = TaskStatus.OnHold;
                return true;
            default:
                return false;
        }
    }

    /// <summary>
    /// Converts a TaskStatus to its snake_case string representation.
    /// </summary>
    public static string ToSnakeCase(this TaskStatus status)
    {
        return status switch
        {
            TaskStatus.Pending => "pending",
            TaskStatus.InProgress => "in_progress",
            TaskStatus.Completed => "completed",
            TaskStatus.Cancelled => "cancelled",
            TaskStatus.OnHold => "on_hold",
            _ => status.ToString().ToLowerInvariant()
        };
    }
}
