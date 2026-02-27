using Microsoft.AspNetCore.Mvc;

namespace TaskManagementApi.Models;

/// <summary>
/// Represents query parameters for listing tasks.
/// Mirrors the Go ListTasksQuery struct with form binding tags.
/// </summary>
public class ListTasksQuery
{
    /// <summary>
    /// Number of tasks per page. Default: 20, Min: 1, Max: 100.
    /// </summary>
    [FromQuery(Name = "page_size")]
    public int PageSize { get; set; } = 20;

    /// <summary>
    /// Token for the next page (offset-based, string representation of start index).
    /// </summary>
    [FromQuery(Name = "page_token")]
    public string? PageToken { get; set; }

    /// <summary>
    /// Filter by task status.
    /// </summary>
    [FromQuery(Name = "status")]
    public string? Status { get; set; }

    /// <summary>
    /// Filter by assigned user.
    /// </summary>
    [FromQuery(Name = "assigned_to")]
    public string? AssignedTo { get; set; }

    /// <summary>
    /// Filter by tags (comma-separated). Task must have ALL specified tags.
    /// </summary>
    [FromQuery(Name = "tags")]
    public string? Tags { get; set; }

    /// <summary>
    /// Sort order for results.
    /// </summary>
    [FromQuery(Name = "sort_order")]
    public string? SortOrder { get; set; }
}
