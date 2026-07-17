"""Hardening tests for the authentication API."""

import uuid

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.users import create_user
from app.main import app
from app.models.user import User, UserStatus
from app.models.user_credential import UserCredential
from app.models.user_session import UserSession
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

client = TestClient(app)

TEST_PASSWORD = "correct horse battery staple"


def create_hardening_identity(
    *,
    status: UserStatus = UserStatus.ACTIVE,
) -> tuple[str, uuid.UUID]:
    """Create a temporary identity for authentication-hardening tests."""

    with SessionLocal() as session:
        user = create_user(
            session,
            username=f"auth-hardening-{uuid.uuid4().hex}",
            display_name="Authentication Hardening User",
        )
        user.status = status

        create_user_credential(
            session,
            user_id=user.id,
            password=TEST_PASSWORD,
        )

        session.commit()

        return user.username, user.id


def delete_hardening_identity(user_id: uuid.UUID) -> None:
    """Delete a temporary hardening-test identity."""

    client.cookies.clear()

    with SessionLocal() as session:
        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_disabled_account_receives_generic_login_failure() -> None:
    """Disabled users should receive the generic unauthorized response."""

    username, user_id = create_hardening_identity(
        status=UserStatus.DISABLED,
    )

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 401
        assert response.json() == {
            "detail": "Invalid username or password.",
        }

        with SessionLocal() as session:
            stored_sessions = session.scalars(
                select(UserSession).where(UserSession.user_id == user_id)
            ).all()

            assert stored_sessions == []
    finally:
        delete_hardening_identity(user_id)


def test_repeated_invalid_logins_lock_account_without_creating_session() -> None:
    """Repeated invalid passwords should trigger the credential lockout."""

    username, user_id = create_hardening_identity()

    try:
        for _ in range(5):
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

        locked_response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert locked_response.status_code == 401
        assert locked_response.json() == {
            "detail": "Invalid username or password.",
        }

        with SessionLocal() as session:
            credential = session.get(UserCredential, user_id)

            assert credential is not None
            assert credential.failed_login_count >= 5
            assert credential.locked_until is not None

            stored_sessions = session.scalars(
                select(UserSession).where(UserSession.user_id == user_id)
            ).all()

            assert stored_sessions == []
    finally:
        delete_hardening_identity(user_id)


def test_login_cookie_includes_expected_security_attributes() -> None:
    """A login cookie should include its lifetime and safety attributes."""

    username, user_id = create_hardening_identity()

    try:
        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200

        set_cookie = response.headers["set-cookie"]

        assert "choretracker_session=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Max-Age=" in set_cookie
        assert "Path=/" in set_cookie
        assert "SameSite=lax" in set_cookie
    finally:
        delete_hardening_identity(user_id)


def test_secure_cookie_setting_adds_secure_attribute(
    monkeypatch,
) -> None:
    """HTTPS deployments should emit cookies with the Secure attribute."""

    username, user_id = create_hardening_identity()

    try:
        monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
        get_settings.cache_clear()

        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"]
    finally:
        get_settings.cache_clear()
        delete_hardening_identity(user_id)
