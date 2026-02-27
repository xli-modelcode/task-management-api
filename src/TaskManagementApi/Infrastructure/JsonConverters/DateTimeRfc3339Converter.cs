using System.Text.Json;
using System.Text.Json.Serialization;

namespace TaskManagementApi.Infrastructure.JsonConverters;

/// <summary>
/// Serializes DateTime values in RFC 3339 format without fractional seconds,
/// matching Go's time.RFC3339 output: "2006-01-02T15:04:05Z07:00".
/// Go truncates to second precision on output; this converter does the same.
/// </summary>
public class DateTimeRfc3339Converter : JsonConverter<DateTime>
{
    private const string Format = "yyyy-MM-ddTHH:mm:ssZ";

    public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        return reader.GetDateTime();
    }

    public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
    {
        writer.WriteStringValue(value.ToUniversalTime().ToString(Format));
    }
}

/// <summary>
/// Serializes nullable DateTime values in RFC 3339 format without fractional seconds.
/// </summary>
public class NullableDateTimeRfc3339Converter : JsonConverter<DateTime?>
{
    private const string Format = "yyyy-MM-ddTHH:mm:ssZ";

    public override DateTime? Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        return reader.GetDateTime();
    }

    public override void Write(Utf8JsonWriter writer, DateTime? value, JsonSerializerOptions options)
    {
        if (value.HasValue)
        {
            writer.WriteStringValue(value.Value.ToUniversalTime().ToString(Format));
        }
        else
        {
            writer.WriteNullValue();
        }
    }
}
