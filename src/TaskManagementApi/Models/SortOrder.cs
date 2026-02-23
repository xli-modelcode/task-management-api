namespace TaskManagementApi.Models;

/// <summary>
/// Represents the sort order for task listing.
/// Global JsonStringEnumConverter with SnakeCaseLower in Program.cs handles serialization.
/// </summary>
public enum SortOrder
{
    CreatedAtAsc,
    CreatedAtDesc,
    DueDateAsc,
    DueDateDesc,
    PriorityAsc,
    PriorityDesc
}
