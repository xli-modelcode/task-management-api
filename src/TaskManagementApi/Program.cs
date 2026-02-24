using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Mvc;
using TaskManagementApi.Infrastructure.ErrorHandling;
using TaskManagementApi.Infrastructure.JsonConverters;
using TaskManagementApi.Models.Responses;
using TaskManagementApi.Services;

var builder = WebApplication.CreateBuilder(args);

// Support Go's PORT env var for backward compatibility (defaults to 8080).
// ASPNETCORE_URLS takes precedence if set; launchSettings.json applies in development.
var port = Environment.GetEnvironmentVariable("PORT") ?? "8080";
builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

// Configure JSON serialization to match Go's JSON behavior:
// - snake_case field names (matching Go json tags)
// - String enum serialization with snake_case (e.g., "in_progress", "on_hold")
// Note: Go's omitempty is handled per-property via [JsonIgnore(Condition = WhenWritingNull)]
// attributes on model fields. A global DefaultIgnoreCondition is NOT used because Go only
// omits fields explicitly tagged with omitempty; non-omitempty nullable fields serialize as null.
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
        options.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
        // Match Go's time.RFC3339 output (no fractional seconds)
        options.JsonSerializerOptions.Converters.Add(new DateTimeRfc3339Converter());
        options.JsonSerializerOptions.Converters.Add(new NullableDateTimeRfc3339Converter());
    });

// Configure API behavior to suppress default ProblemDetails format for validation errors.
// Instead, use a custom factory that returns the Go-compatible error contract:
// {"error": {"code": "VALIDATION_ERROR", "message": "..."}}
builder.Services.Configure<ApiBehaviorOptions>(options =>
{
    options.InvalidModelStateResponseFactory = context =>
    {
        // Collect all model state error messages into a single message
        var errors = context.ModelState
            .Where(e => e.Value?.Errors.Count > 0)
            .SelectMany(e => e.Value!.Errors.Select(err =>
                string.IsNullOrEmpty(err.ErrorMessage) ? err.Exception?.Message ?? "Invalid value" : err.ErrorMessage))
            .ToList();

        var message = string.Join("; ", errors);

        var errorResponse = new ErrorResponse
        {
            Error = new ErrorDetail
            {
                Code = "VALIDATION_ERROR",
                Message = message,
            }
        };

        return new BadRequestObjectResult(errorResponse);
    };
});

// Register TaskService as a singleton (in-memory shared store, matching Go's single service instance)
builder.Services.AddSingleton<TaskService>();

// Configure CORS to match Go's corsMiddleware (allow all origins, specific methods/headers)
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .WithMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
              .WithHeaders("Origin", "Content-Type", "Accept", "Authorization");
    });
});

var app = builder.Build();

// Enable CORS middleware (must be before routing/endpoints)
app.UseCors();

// Add exception handling middleware to catch NotFoundException, ValidationException, etc.
// and convert them to the standard error response format.
// Must be registered before MapControllers so it wraps all endpoint invocations.
app.UseMiddleware<ApiExceptionMiddleware>();

app.MapControllers();

// Log startup information matching Go's console output
var logger = app.Services.GetRequiredService<ILogger<Program>>();
logger.LogInformation("REST API server starting on http://localhost:{Port}", port);
logger.LogInformation("Health check: http://localhost:{Port}/health", port);
logger.LogInformation("API endpoint: http://localhost:{Port}/api/v1/tasks", port);

app.Run();

// Make the Program class accessible for integration tests (WebApplicationFactory)
public partial class Program { }
