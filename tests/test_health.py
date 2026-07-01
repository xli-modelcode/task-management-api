from datetime import datetime


class TestHealthEndpoint:
    """Tests for the GET /health endpoint."""

    def test_health_returns_200(self, client):
        """Verify response status is 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_expected_fields(self, client):
        """Verify JSON contains exactly: status, timestamp, service, version."""
        response = client.get("/health")
        data = response.get_json()
        assert set(data.keys()) == {"status", "timestamp", "service", "version"}

    def test_health_field_values(self, client):
        """Verify status, service, and version field values."""
        response = client.get("/health")
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "task-api-go"
        assert data["version"] == "1.0.0"

    def test_health_timestamp_format(self, client):
        """Verify timestamp matches RFC3339 format with Z suffix."""
        response = client.get("/health")
        data = response.get_json()
        ts = data["timestamp"]
        # Should not raise if format is correct
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        assert parsed is not None
