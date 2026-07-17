"""Integration tests for password authentication."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.session import SessionLocal
from app.domain.identity.authentication import (
    LOCKOUT_DURATION,
    MAXIMUM_FAILED_LOGIN_ATTEMPTS,
    AccountDisabledError,
    AccountLockedError,
    AuthenticationFailedError,
    authenticate_user,
)
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.users import create_user
from app.models.user import User, UserStatus
from app.models.user_credential import UserCredential
from sqlalchemy import delete

TEST_PASSWORD = "correct horse battery staple"


def create_test_identity(
    session,
    *,
    status: UserStatus = UserStatus.ACTIVE,
) -> tuple[User, UserCredential]:
    """Create a temporary user and credential for authentication tests."""

    user = create_user(
        session,
        username=f"auth-{uuid.uuid4().hex}",
        display_name="Authentication Test User",
    )
    user.status = status

    credential = create_user_credential(
        session,
        user_id=user.id,
        password=TEST_PASSWORD,
    )

    session.commit()

    return user, credential


def delete_test_identity(session, user_id) -> None:
    """Delete a temporary user and its cascading credential."""

    session.execute(delete(User).where(User.id == user_id))
    session.commit()


def test_authenticate_user_accepts_normalized_username() -> None:
    """Authentication should normalize case and surrounding whitespace."""

    with SessionLocal() as session:
        user, credential = create_test_identity(session)
        user_id = user.id

        authenticated_user = authenticate_user(
            session,
            username=f"  {user.username.upper()}  ",
            password=TEST_PASSWORD,
        )
        session.commit()

        assert authenticated_user.id == user_id
        assert credential.failed_login_count == 0
        assert credential.locked_until is None

        delete_test_identity(session, user_id)


def test_authenticate_user_rejects_unknown_username() -> None:
    """Unknown usernames should return the generic authentication failure."""

    with SessionLocal() as session, pytest.raises(AuthenticationFailedError):
        authenticate_user(
            session,
            username=f"unknown-{uuid.uuid4().hex}",
            password=TEST_PASSWORD,
        )


def test_authenticate_user_records_failed_password() -> None:
    """An incorrect password should increment the failed-attempt count."""

    with SessionLocal() as session:
        user, credential = create_test_identity(session)
        user_id = user.id

        with pytest.raises(AuthenticationFailedError):
            authenticate_user(
                session,
                username=user.username,
                password="incorrect password value",
            )

        session.commit()

        assert credential.failed_login_count == 1
        assert credential.locked_until is None

        delete_test_identity(session, user_id)


def test_authenticate_user_locks_after_repeated_failures() -> None:
    """Repeated failures should temporarily lock the credential."""

    current_time = datetime.now(UTC)

    with SessionLocal() as session:
        user, credential = create_test_identity(session)
        user_id = user.id

        for _ in range(MAXIMUM_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises(AuthenticationFailedError):
                authenticate_user(
                    session,
                    username=user.username,
                    password="incorrect password value",
                    now=current_time,
                )
            session.commit()

        assert credential.failed_login_count == MAXIMUM_FAILED_LOGIN_ATTEMPTS
        assert credential.locked_until == current_time + LOCKOUT_DURATION

        with pytest.raises(AccountLockedError):
            authenticate_user(
                session,
                username=user.username,
                password=TEST_PASSWORD,
                now=current_time + timedelta(minutes=1),
            )

        delete_test_identity(session, user_id)


def test_authenticate_user_resets_prior_failures_after_success() -> None:
    """Successful authentication should clear temporary failure state."""

    with SessionLocal() as session:
        user, credential = create_test_identity(session)
        user_id = user.id

        credential.failed_login_count = 3
        credential.locked_until = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

        authenticate_user(
            session,
            username=user.username,
            password=TEST_PASSWORD,
        )
        session.commit()

        assert credential.failed_login_count == 0
        assert credential.locked_until is None

        delete_test_identity(session, user_id)


def test_authenticate_user_rejects_disabled_account() -> None:
    """A disabled user must not authenticate with a valid password."""

    with SessionLocal() as session:
        user, _credential = create_test_identity(
            session,
            status=UserStatus.DISABLED,
        )
        user_id = user.id

        with pytest.raises(AccountDisabledError):
            authenticate_user(
                session,
                username=user.username,
                password=TEST_PASSWORD,
            )

        delete_test_identity(session, user_id)
