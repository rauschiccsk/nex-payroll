"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify /health returns 200 with status=healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
