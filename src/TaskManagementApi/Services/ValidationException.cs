namespace TaskManagementApi.Services;

/// <summary>
/// Exception thrown when input validation fails.
/// Maps to HTTP 400 / error code "VALIDATION_ERROR".
/// </summary>
public class ValidationException : Exception
{
    public ValidationException(string message) : base(message)
    {
    }

    public ValidationException(string message, Exception innerException) : base(message, innerException)
    {
    }
}
