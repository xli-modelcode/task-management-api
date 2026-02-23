using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace TaskManagementApi.Models.Requests;

/// <summary>
/// Represents a request to update the status of a task.
/// Mirrors the Go UpdateTaskStatusRequest with required status binding.
/// </summary>
public class UpdateTaskStatusRequest
{
    [JsonPropertyName("status")]
    [Required(ErrorMessage = "status is required")]
    public TaskStatus? Status { get; set; }
}
