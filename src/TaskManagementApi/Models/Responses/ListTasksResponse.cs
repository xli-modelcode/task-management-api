using System.Text.Json.Serialization;

namespace TaskManagementApi.Models.Responses;

/// <summary>
/// Represents the response for listing tasks.
/// Mirrors the Go ListTasksResponse struct.
/// </summary>
public class ListTasksResponse
{
    [JsonPropertyName("tasks")]
    public List<TaskModel> Tasks { get; set; } = new();

    [JsonPropertyName("next_page_token")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? NextPageToken { get; set; }

    [JsonPropertyName("total_count")]
    public int TotalCount { get; set; }
}
