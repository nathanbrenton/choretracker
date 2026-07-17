"""Tests for the server-managed user session model."""

from app.models.user_session import UserSession


def test_user_session_contains_security_fields() -> None:
    """Session records should contain lifecycle and token-hash fields."""

    columns = UserSession.__table__.columns

    assert "id" in columns
    assert "user_id" in columns
    assert "token_hash" in columns
    assert "expires_at" in columns
    assert "last_used_at" in columns
    assert "revoked_at" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_session_token_hash_is_unique_and_required() -> None:
    """Stored token hashes should uniquely identify sessions."""

    token_hash_column = UserSession.__table__.columns["token_hash"]

    assert token_hash_column.nullable is False
    assert token_hash_column.unique is True
    assert token_hash_column.type.length == 64


def test_session_user_foreign_key_cascades() -> None:
    """Deleting a user should remove their login sessions."""

    user_id_column = UserSession.__table__.columns["user_id"]
    foreign_key = next(iter(user_id_column.foreign_keys))

    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"


def test_session_lifecycle_timestamps_are_required_as_expected() -> None:
    """Expiry is required while use and revocation timestamps are optional."""

    columns = UserSession.__table__.columns

    assert columns["expires_at"].nullable is False
    assert columns["last_used_at"].nullable is True
    assert columns["revoked_at"].nullable is True
