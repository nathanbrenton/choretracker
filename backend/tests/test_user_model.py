"""Tests for the initial ChoreTracker user model."""

from app.models.user import User, UserStatus


def test_user_table_uses_expected_name() -> None:
    """The user model should map to the users table."""

    assert User.__tablename__ == "users"


def test_user_model_defines_identity_columns() -> None:
    """The user table should contain its initial identity fields."""

    columns = User.__table__.columns

    assert "id" in columns
    assert "username" in columns
    assert "display_name" in columns
    assert "status" in columns
    assert "is_developer" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_username_is_unique_and_indexed() -> None:
    """Usernames should support unique login identity lookup."""

    username_column = User.__table__.columns["username"]

    assert username_column.unique is True
    assert username_column.index is True
    assert username_column.nullable is False


def test_user_status_values_are_explicit() -> None:
    """Account states should remain stable domain values."""

    assert UserStatus.ACTIVE.value == "active"
    assert UserStatus.DISABLED.value == "disabled"


def test_developer_access_defaults_to_disabled() -> None:
    """New users should not receive developer access by default."""

    developer_column = User.__table__.columns["is_developer"]

    assert developer_column.default is not None
    assert developer_column.default.arg is False
