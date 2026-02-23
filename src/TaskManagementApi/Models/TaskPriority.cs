namespace TaskManagementApi.Models;

/// <summary>
/// Represents the priority level of a task.
/// Global JsonStringEnumConverter with SnakeCaseLower in Program.cs handles serialization.
/// </summary>
public enum TaskPriority
{
    Low,
    Medium,
    High,
    Critical
}

public static class TaskPriorityExtensions
{
    /// <summary>
    /// Validates whether the given TaskPriority value is a defined enum member.
    /// </summary>
    public static bool IsValid(this TaskPriority priority)
    {
        return priority is TaskPriority.Low
            or TaskPriority.Medium
            or TaskPriority.High
            or TaskPriority.Critical;
    }

    /// <summary>
    /// Returns a numeric value for priority sorting (matches Go GetValue()).
    /// </summary>
    public static int GetValue(this TaskPriority priority)
    {
        return priority switch
        {
            TaskPriority.Low => 1,
            TaskPriority.Medium => 2,
            TaskPriority.High => 3,
            TaskPriority.Critical => 4,
            _ => 2 // default matches Go behavior
        };
    }

    /// <summary>
    /// Tries to parse a string into a TaskPriority value using snake_case convention.
    /// </summary>
    public static bool TryParseSnakeCase(string? value, out TaskPriority result)
    {
        result = default;
        if (string.IsNullOrEmpty(value))
            return false;

        switch (value)
        {
            case "low":
                result = TaskPriority.Low;
                return true;
            case "medium":
                result = TaskPriority.Medium;
                return true;
            case "high":
                result = TaskPriority.High;
                return true;
            case "critical":
                result = TaskPriority.Critical;
                return true;
            default:
                return false;
        }
    }

    /// <summary>
    /// Converts a TaskPriority to its snake_case string representation.
    /// </summary>
    public static string ToSnakeCase(this TaskPriority priority)
    {
        return priority switch
        {
            TaskPriority.Low => "low",
            TaskPriority.Medium => "medium",
            TaskPriority.High => "high",
            TaskPriority.Critical => "critical",
            _ => priority.ToString().ToLowerInvariant()
        };
    }
}
