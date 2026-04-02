"""Tests for the /health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_body():
    """GET /health should return JSON with status 'ok'."""
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
