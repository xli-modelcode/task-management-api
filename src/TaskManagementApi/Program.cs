using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Mvc;
using TaskManagementApi.Infrastructure.ErrorHandling;
using TaskManagementApi.Models.Responses;
using TaskManagementApi.Services;

var builder = WebApplication.CreateBuilder(args);

// Configure JSON serialization to match Go's JSON behavior:
// - snake_case field names (matching Go json tags)
// - String enum serialization with snake_case (e.g., "in_progress", "on_hold")
// - Null fields omitted from output (matching Go's omitempty)
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
        options.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
        options.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
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

app.Run();

// Make the Program class accessible for integration tests (WebApplicationFactory)
public partial class Program { }
