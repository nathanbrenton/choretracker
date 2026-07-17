"""Integration tests for PostgreSQL connectivity."""

from app.db.session import check_database_connection


def test_application_can_connect_to_postgresql() -> None:
    """The configured PostgreSQL service should accept application queries."""

    assert check_database_connection() is True
