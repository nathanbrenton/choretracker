"""Integration tests for server-managed authentication sessions."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.session import SessionLocal
from app.domain.identity.sessions import (
    DEFAULT_SESSION_LIFETIME,
    SessionExpiredError,
    SessionNotFoundError,
    SessionRevokedError,
    UserNotFoundError,
    create_user_session,
    get_active_session,
    hash_session_token,
    revoke_session,
)
from app.domain.identity.users import create_user
from app.models.user import User
from app.models.user_session import UserSession
from sqlalchemy import delete


def create_test_user(session) -> User:
    """Create one temporary user for session tests."""

    user = create_user(
        session,
        username=f"session-{uuid.uuid4().hex}",
        display_name="Session Test User",
    )
    session.commit()

    return user


def delete_test_user(session, user_id) -> None:
    """Delete a temporary user and cascading sessions."""

    session.execute(delete(User).where(User.id == user_id))
    session.commit()


def test_create_user_session_stores_only_token_hash() -> None:
    """Session creation should return plaintext once and persist only its hash."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=current_time,
        )
        session.commit()

        assert created.token
        assert len(created.session.token_hash) == 64
        assert created.session.token_hash == hash_session_token(created.token)
        assert created.session.token_hash != created.token
        assert created.session.expires_at == (current_time + DEFAULT_SESSION_LIFETIME)
        assert created.session.last_used_at is None
        assert created.session.revoked_at is None

        delete_test_user(session, user_id)


def test_create_user_session_rejects_missing_user() -> None:
    """Sessions must not be created for unknown users."""

    with SessionLocal() as session, pytest.raises(UserNotFoundError):
        create_user_session(
            session,
            user_id=uuid.uuid4(),
        )


def test_get_active_session_updates_last_used_timestamp() -> None:
    """A valid session lookup should record its latest use time."""

    created_at = datetime.now(UTC)
    used_at = created_at + timedelta(minutes=5)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=created_at,
        )
        session.commit()

        loaded_session = get_active_session(
            session,
            token=created.token,
            now=used_at,
        )
        session.commit()

        assert loaded_session.id == created.session.id
        assert loaded_session.last_used_at == used_at

        delete_test_user(session, user_id)


def test_get_active_session_can_skip_last_used_update() -> None:
    """Read-only session checks should optionally avoid a write."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=current_time,
        )
        session.commit()

        loaded_session = get_active_session(
            session,
            token=created.token,
            now=current_time + timedelta(minutes=1),
            update_last_used=False,
        )

        assert loaded_session.last_used_at is None

        delete_test_user(session, user_id)


def test_get_active_session_rejects_unknown_token() -> None:
    """An unknown token should not resolve to a session."""

    with SessionLocal() as session, pytest.raises(SessionNotFoundError):
        get_active_session(
            session,
            token="unknown-session-token",
        )


def test_get_active_session_rejects_expired_session() -> None:
    """Expired sessions must not authenticate a user."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=current_time,
            lifetime=timedelta(minutes=1),
        )
        session.commit()

        with pytest.raises(SessionExpiredError):
            get_active_session(
                session,
                token=created.token,
                now=current_time + timedelta(minutes=2),
            )

        delete_test_user(session, user_id)


def test_revoke_session_prevents_future_use() -> None:
    """Revoked sessions should remain stored but become unusable."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=current_time,
        )
        session.commit()

        revoked = revoke_session(
            session,
            token=created.token,
            now=current_time + timedelta(minutes=1),
        )
        session.commit()

        assert revoked.revoked_at == current_time + timedelta(minutes=1)

        with pytest.raises(SessionRevokedError):
            get_active_session(
                session,
                token=created.token,
                now=current_time + timedelta(minutes=2),
            )

        delete_test_user(session, user_id)


def test_revoke_session_is_idempotent() -> None:
    """Repeated revocation should preserve the original revocation time."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
            now=current_time,
        )
        session.commit()

        first_revocation = current_time + timedelta(minutes=1)
        second_attempt = current_time + timedelta(minutes=2)

        revoke_session(
            session,
            token=created.token,
            now=first_revocation,
        )
        session.commit()

        revoked_again = revoke_session(
            session,
            token=created.token,
            now=second_attempt,
        )
        session.commit()

        assert revoked_again.revoked_at == first_revocation

        delete_test_user(session, user_id)


def test_user_deletion_cascades_to_sessions() -> None:
    """Deleting a user should remove all of their session records."""

    with SessionLocal() as session:
        user = create_test_user(session)
        user_id = user.id

        created = create_user_session(
            session,
            user_id=user_id,
        )
        session.commit()

        session_id = created.session.id

        session.execute(delete(User).where(User.id == user_id))
        session.commit()

    # A fresh session avoids returning a stale object from the identity map.
    with SessionLocal() as verification_session:
        assert verification_session.get(UserSession, session_id) is None
