"""Tests for the ChoreTracker liveness endpoint."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint_returns_success() -> None:
    """The liveness endpoint should confirm the API process is running."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "choretracker",
    }


def test_openapi_uses_configured_application_name() -> None:
    """The generated API schema should use the configured application name."""

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ChoreTracker"
