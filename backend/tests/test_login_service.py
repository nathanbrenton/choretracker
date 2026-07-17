"""Integration tests for the ChoreTracker login use case."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.passwords import verify_password
from app.db.session import SessionLocal
from app.domain.identity.authentication import AuthenticationFailedError
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.login import login_user
from app.domain.identity.sessions import hash_session_token
from app.domain.identity.users import create_user
from app.models.user import User
from app.models.user_session import UserSession
from sqlalchemy import delete

TEST_PASSWORD = "correct horse battery staple"


def create_login_identity(session) -> User:
    """Create a temporary user and credential for login tests."""

    user = create_user(
        session,
        username=f"login-{uuid.uuid4().hex}",
        display_name="Login Test User",
    )

    create_user_credential(
        session,
        user_id=user.id,
        password=TEST_PASSWORD,
    )

    session.commit()

    return user


def delete_login_identity(session, user_id) -> None:
    """Delete a temporary login identity and cascading security records."""

    session.execute(delete(User).where(User.id == user_id))
    session.commit()


def test_login_user_authenticates_and_creates_session() -> None:
    """Valid credentials should create one server-managed session."""

    current_time = datetime.now(UTC)
    lifetime = timedelta(hours=2)

    with SessionLocal() as session:
        user = create_login_identity(session)
        user_id = user.id

        result = login_user(
            session,
            username=f"  {user.username.upper()}  ",
            password=TEST_PASSWORD,
            now=current_time,
            session_lifetime=lifetime,
        )
        session.commit()

        assert result.user.id == user_id
        assert result.token
        assert result.session.user_id == user_id
        assert result.session.token_hash == hash_session_token(result.token)
        assert result.session.token_hash != result.token
        assert result.session.expires_at == current_time + lifetime
        assert result.session.revoked_at is None

        stored_session = session.get(UserSession, result.session.id)

        assert stored_session is not None
        assert stored_session.token_hash == hash_session_token(result.token)

        delete_login_identity(session, user_id)


def test_login_user_rejects_invalid_password_without_session() -> None:
    """Invalid credentials must not create a login session."""

    with SessionLocal() as session:
        user = create_login_identity(session)
        user_id = user.id

        with pytest.raises(AuthenticationFailedError):
            login_user(
                session,
                username=user.username,
                password="incorrect password value",
            )

        session.commit()

        stored_sessions = session.query(UserSession).filter(UserSession.user_id == user_id).all()

        assert stored_sessions == []

        delete_login_identity(session, user_id)


def test_login_user_does_not_store_plaintext_password_or_token() -> None:
    """Stored security records must contain only hashes."""

    with SessionLocal() as session:
        user = create_login_identity(session)
        user_id = user.id

        result = login_user(
            session,
            username=user.username,
            password=TEST_PASSWORD,
        )
        session.commit()

        assert result.session.token_hash != result.token
        assert TEST_PASSWORD not in result.session.token_hash
        assert verify_password(TEST_PASSWORD, result.session.token_hash) is False

        delete_login_identity(session, user_id)
