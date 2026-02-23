using System.Text.Json.Serialization;

namespace TaskManagementApi.Models;

/// <summary>
/// Represents the sort order for task listing.
/// </summary>
[JsonConverter(typeof(JsonStringEnumConverter<SortOrder>))]
public enum SortOrder
{
    CreatedAtAsc,
    CreatedAtDesc,
    DueDateAsc,
    DueDateDesc,
    PriorityAsc,
    PriorityDesc
}
