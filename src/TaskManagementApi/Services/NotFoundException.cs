namespace TaskManagementApi.Services;

/// <summary>
/// Exception thrown when a requested resource is not found.
/// Maps to HTTP 404 / error code "NOT_FOUND".
/// </summary>
public class NotFoundException : Exception
{
    public NotFoundException(string message) : base(message)
    {
    }

    public NotFoundException(string message, Exception innerException) : base(message, innerException)
    {
    }
}
