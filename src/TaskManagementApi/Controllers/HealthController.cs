using Microsoft.AspNetCore.Mvc;

namespace TaskManagementApi.Controllers;

/// <summary>
/// Health check controller. Mirrors Go's healthCheck handler.
/// </summary>
[ApiController]
public class HealthController : ControllerBase
{
    /// <summary>
    /// GET /health - Returns service health status.
    /// Response matches Go handler output:
    /// {"status": "healthy", "timestamp": "RFC3339", "service": "task-api-go", "version": "1.0.0"}
    /// </summary>
    [HttpGet("/health")]
    public IActionResult HealthCheck()
    {
        return Ok(new
        {
            status = "healthy",
            timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ"),
            service = "task-api-go",
            version = "1.0.0"
        });
    }
}
