"""API tests for the login endpoint."""

import uuid

from app.db.session import SessionLocal
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.users import create_user
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import delete

client = TestClient(app)

TEST_PASSWORD = "correct horse battery staple"


def create_api_login_identity() -> tuple[str, uuid.UUID]:
    """Create one temporary login identity for API tests."""

    with SessionLocal() as session:
        user = create_user(
            session,
            username=f"api-login-{uuid.uuid4().hex}",
            display_name="API Login User",
        )

        create_user_credential(
            session,
            user_id=user.id,
            password=TEST_PASSWORD,
        )

        session.commit()

        return user.username, user.id


def delete_api_login_identity(user_id: uuid.UUID) -> None:
    """Delete the temporary API login identity."""

    with SessionLocal() as session:
        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_login_endpoint_sets_http_only_cookie() -> None:
    """Valid credentials should establish an HTTP-only session cookie."""

    username, user_id = create_api_login_identity()

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert response.json()["user"]["username"] == username
        assert response.json()["must_change_password"] is False
        assert "token" not in response.json()

        set_cookie = response.headers["set-cookie"]

        assert "choretracker_session=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie
    finally:
        delete_api_login_identity(user_id)


def test_login_endpoint_rejects_invalid_password() -> None:
    """Invalid credentials should return a generic unauthorized response."""

    username, user_id = create_api_login_identity()

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": "incorrect password value",
            },
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Invalid username or password.",
        }
        assert "set-cookie" not in response.headers
    finally:
        delete_api_login_identity(user_id)


def test_login_endpoint_rejects_unknown_username() -> None:
    """Unknown usernames should receive the same generic failure."""

    response = client.post(
        "/auth/login",
        json={
            "username": f"unknown-{uuid.uuid4().hex}",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid username or password.",
    }
