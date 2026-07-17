"""Tests for the ChoreTracker readiness endpoint."""

from unittest.mock import patch

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_readiness_returns_success_when_database_is_available() -> None:
    """Readiness should succeed when PostgreSQL accepts connections."""

    with patch(
        "app.api.readiness.check_database_connection",
        return_value=True,
    ):
        response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "available",
    }


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    """Readiness should fail safely when PostgreSQL is unavailable."""

    with patch(
        "app.api.readiness.check_database_connection",
        return_value=False,
    ):
        response = client.get("/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "unavailable",
    }
