using System.Text.Json;
using TaskManagementApi.Models.Responses;
using TaskManagementApi.Services;

namespace TaskManagementApi.Infrastructure.ErrorHandling;

/// <summary>
/// Middleware that catches exceptions thrown by downstream components and converts them
/// into the standard error response format: {"error": {"code": "...", "message": "..."}}.
/// This centralizes error mapping that in the Go version was done inline in each handler.
/// </summary>
public class ApiExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ApiExceptionMiddleware> _logger;

    public ApiExceptionMiddleware(RequestDelegate next, ILogger<ApiExceptionMiddleware> logger)
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (NotFoundException ex)
        {
            _logger.LogWarning(ex, "Resource not found: {Message}", ex.Message);
            await WriteErrorResponse(context, StatusCodes.Status404NotFound, "NOT_FOUND", ex.Message);
        }
        catch (ValidationException ex)
        {
            _logger.LogWarning(ex, "Validation error: {Message}", ex.Message);
            await WriteErrorResponse(context, StatusCodes.Status400BadRequest, "VALIDATION_ERROR", ex.Message);
        }
        catch (JsonException ex)
        {
            _logger.LogWarning(ex, "JSON parsing error: {Message}", ex.Message);
            await WriteErrorResponse(context, StatusCodes.Status400BadRequest, "VALIDATION_ERROR", ex.Message);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception: {Message}", ex.Message);
            await WriteErrorResponse(context, StatusCodes.Status500InternalServerError, "INTERNAL_ERROR", ex.Message);
        }
    }

    private static async Task WriteErrorResponse(HttpContext context, int statusCode, string code, string message)
    {
        context.Response.StatusCode = statusCode;
        context.Response.ContentType = "application/json";

        var errorResponse = new ErrorResponse
        {
            Error = new ErrorDetail
            {
                Code = code,
                Message = message,
            }
        };

        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        };

        await context.Response.WriteAsJsonAsync(errorResponse, options);
    }
}
