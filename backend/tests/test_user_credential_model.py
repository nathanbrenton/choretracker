"""Tests for the password credential model."""

from app.models.user_credential import UserCredential


def test_user_credential_uses_one_to_one_primary_key() -> None:
    """The user foreign key should also enforce one credential per user."""

    user_id_column = UserCredential.__table__.columns["user_id"]

    assert user_id_column.primary_key is True
    assert len(user_id_column.foreign_keys) == 1

    foreign_key = next(iter(user_id_column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_user_credential_contains_security_fields() -> None:
    """Credential records should contain the planned authentication fields."""

    columns = UserCredential.__table__.columns

    assert "password_hash" in columns
    assert "password_changed_at" in columns
    assert "must_change_password" in columns
    assert "failed_login_count" in columns
    assert "locked_until" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_password_hash_is_required() -> None:
    """A credential row must always contain a password hash."""

    password_hash_column = UserCredential.__table__.columns["password_hash"]

    assert password_hash_column.nullable is False
    assert password_hash_column.type.length == 512


def test_lockout_defaults_are_safe() -> None:
    """New credentials should begin unlocked with no failed attempts."""

    failed_login_column = UserCredential.__table__.columns["failed_login_count"]
    must_change_column = UserCredential.__table__.columns["must_change_password"]
    locked_until_column = UserCredential.__table__.columns["locked_until"]

    assert failed_login_column.default is not None
    assert failed_login_column.default.arg == 0
    assert must_change_column.default is not None
    assert must_change_column.default.arg is False
    assert locked_until_column.nullable is True
