using System.Text.Json;
using System.Text.Json.Serialization;
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

app.MapControllers();

app.Run();

// Make the Program class accessible for integration tests (WebApplicationFactory)
public partial class Program { }
