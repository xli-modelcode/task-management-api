using System.Text.Json.Serialization;

namespace TaskManagementApi.Models.Responses;

/// <summary>
/// Represents an error response. Mirrors the Go ErrorResponse struct.
/// </summary>
public class ErrorResponse
{
    [JsonPropertyName("error")]
    public ErrorDetail Error { get; set; } = new();
}

/// <summary>
/// Contains error details. Mirrors the Go ErrorDetail struct.
/// </summary>
public class ErrorDetail
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("details")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public object? Details { get; set; }
}
