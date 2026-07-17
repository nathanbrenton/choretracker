"""API tests for the logout endpoint."""

import uuid

from app.db.session import SessionLocal
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.users import create_user
from app.main import app
from app.models.user import User
from app.models.user_session import UserSession
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

client = TestClient(app)

TEST_PASSWORD = "correct horse battery staple"


def create_logout_identity() -> tuple[str, uuid.UUID]:
    """Create one temporary identity for logout tests."""

    with SessionLocal() as session:
        user = create_user(
            session,
            username=f"logout-{uuid.uuid4().hex}",
            display_name="Logout Test User",
        )

        create_user_credential(
            session,
            user_id=user.id,
            password=TEST_PASSWORD,
        )

        session.commit()

        return user.username, user.id


def delete_logout_identity(user_id: uuid.UUID) -> None:
    """Delete a temporary logout identity."""

    with SessionLocal() as session:
        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_logout_revokes_session_and_clears_cookie() -> None:
    """Logout should revoke the server session and clear the cookie."""

    username, user_id = create_logout_identity()

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

        response = client.post("/auth/logout")

        assert response.status_code == 204
        assert client.cookies.get("choretracker_session") is None

        set_cookie = response.headers["set-cookie"]

        assert "choretracker_session=" in set_cookie
        assert "Max-Age=0" in set_cookie

        with SessionLocal() as session:
            stored_session = session.scalar(
                select(UserSession).where(UserSession.user_id == user_id)
            )

            assert stored_session is not None
            assert stored_session.revoked_at is not None

        me_response = client.get("/auth/me")

        assert me_response.status_code == 401
    finally:
        client.cookies.clear()
        delete_logout_identity(user_id)


def test_logout_without_cookie_is_idempotent() -> None:
    """Logging out without a session should still succeed."""

    client.cookies.clear()

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert client.cookies.get("choretracker_session") is None


def test_logout_with_unknown_cookie_is_idempotent() -> None:
    """An unknown cookie should be cleared without revealing token state."""

    client.cookies.set(
        "choretracker_session",
        "unknown-session-token",
    )

    try:
        response = client.post("/auth/logout")

        assert response.status_code == 204

        set_cookie = response.headers["set-cookie"]

        assert "choretracker_session=" in set_cookie
        assert "Max-Age=0" in set_cookie
    finally:
        client.cookies.clear()
