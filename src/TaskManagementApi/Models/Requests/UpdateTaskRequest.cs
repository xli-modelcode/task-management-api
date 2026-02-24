using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace TaskManagementApi.Models.Requests;

/// <summary>
/// Represents a request to update an existing task.
/// All fields are nullable to support partial updates (mirrors Go pointer fields).
/// </summary>
public class UpdateTaskRequest
{
    [JsonPropertyName("title")]
    [StringLength(200, MinimumLength = 1, ErrorMessage = "title must be between 1 and 200 characters")]
    public string? Title { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("status")]
    public TaskStatus? Status { get; set; }

    [JsonPropertyName("priority")]
    public TaskPriority? Priority { get; set; }

    [JsonPropertyName("tags")]
    public List<string>? Tags { get; set; }

    [JsonPropertyName("assigned_to")]
    public string? AssignedTo { get; set; }

    [JsonPropertyName("due_date")]
    public DateTime? DueDate { get; set; }
}
