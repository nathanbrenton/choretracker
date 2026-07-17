"""API tests for authenticated current-user resolution."""

import uuid

from app.db.session import SessionLocal
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.sessions import revoke_session
from app.domain.identity.users import create_user
from app.main import app
from app.models.user import User
from app.models.user_session import UserSession
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

client = TestClient(app)

TEST_PASSWORD = "correct horse battery staple"


def create_authenticated_identity() -> tuple[str, uuid.UUID]:
    """Create one temporary user with a password credential."""

    with SessionLocal() as session:
        user = create_user(
            session,
            username=f"me-{uuid.uuid4().hex}",
            display_name="Current User Test",
        )

        create_user_credential(
            session,
            user_id=user.id,
            password=TEST_PASSWORD,
        )

        session.commit()

        return user.username, user.id


def delete_authenticated_identity(user_id: uuid.UUID) -> None:
    """Delete a temporary authenticated identity."""

    with SessionLocal() as session:
        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_me_endpoint_returns_authenticated_user() -> None:
    """A valid login cookie should resolve the current user."""

    username, user_id = create_authenticated_identity()

    try:
        login_response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        response = client.get("/auth/me")

        assert response.status_code == 200
        assert response.json() == {
            "id": str(user_id),
            "username": username,
            "display_name": "Current User Test",
            "status": "active",
            "is_developer": False,
        }
    finally:
        client.cookies.clear()
        delete_authenticated_identity(user_id)


def test_me_endpoint_rejects_missing_cookie() -> None:
    """A request without a session cookie should be unauthorized."""

    client.cookies.clear()

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }


def test_me_endpoint_rejects_invalid_cookie() -> None:
    """An unknown session token should be unauthorized."""

    client.cookies.set(
        "choretracker_session",
        "unknown-session-token",
    )

    try:
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Authentication required.",
        }
    finally:
        client.cookies.clear()


def test_me_endpoint_rejects_revoked_session() -> None:
    """A revoked session cookie should no longer authenticate."""

    username, user_id = create_authenticated_identity()

    try:
        login_response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        token = client.cookies.get("choretracker_session")

        assert token is not None

        with SessionLocal() as session:
            revoke_session(
                session,
                token=token,
            )
            session.commit()

        response = client.get("/auth/me")

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Authentication required.",
        }
    finally:
        client.cookies.clear()
        delete_authenticated_identity(user_id)


def test_me_endpoint_updates_session_last_used() -> None:
    """Successful current-user resolution should update session activity."""

    username, user_id = create_authenticated_identity()

    try:
        login_response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert login_response.status_code == 200

        token = client.cookies.get("choretracker_session")

        assert token is not None

        response = client.get("/auth/me")

        assert response.status_code == 200

        with SessionLocal() as session:
            stored_session = session.scalar(
                select(UserSession).where(UserSession.user_id == user_id)
            )

            assert stored_session is not None
            assert stored_session.last_used_at is not None
    finally:
        client.cookies.clear()
        delete_authenticated_identity(user_id)
