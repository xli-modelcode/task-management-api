using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace TaskManagementApi.Models.Requests;

/// <summary>
/// Represents a request to create a new task.
/// Mirrors the Go CreateTaskRequest struct with Gin binding rules.
/// </summary>
public class CreateTaskRequest
{
    [JsonPropertyName("title")]
    [Required(ErrorMessage = "title is required")]
    [StringLength(200, MinimumLength = 1, ErrorMessage = "title must be between 1 and 200 characters")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("priority")]
    public TaskPriority? Priority { get; set; }

    [JsonPropertyName("tags")]
    public List<string>? Tags { get; set; }

    [JsonPropertyName("assigned_to")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? AssignedTo { get; set; }

    [JsonPropertyName("due_date")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public DateTime? DueDate { get; set; }
}
