"""Password authentication use cases."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.passwords import verify_password
from app.domain.identity.usernames import normalize_username
from app.models.user import User, UserStatus
from app.models.user_credential import UserCredential

MAXIMUM_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


class AuthenticationFailedError(ValueError):
    """Raised when supplied credentials cannot authenticate a user."""


class AccountDisabledError(ValueError):
    """Raised when a disabled account attempts to authenticate."""


class AccountLockedError(ValueError):
    """Raised when a credential is temporarily locked."""


def authenticate_user(
    session: Session,
    *,
    username: str,
    password: str,
    now: datetime | None = None,
) -> User:
    """Authenticate one active user with a password credential."""

    current_time = now or datetime.now(UTC)
    normalized_username = normalize_username(username)

    user = session.scalar(select(User).where(User.username == normalized_username))

    if user is None:
        raise AuthenticationFailedError("Invalid username or password.")

    if user.status == UserStatus.DISABLED:
        raise AccountDisabledError("This account is disabled.")

    credential = session.get(UserCredential, user.id)

    if credential is None:
        raise AuthenticationFailedError("Invalid username or password.")

    if credential.locked_until is not None and credential.locked_until > current_time:
        raise AccountLockedError("This account is temporarily locked.")

    if not verify_password(password, credential.password_hash):
        credential.failed_login_count += 1

        if credential.failed_login_count >= MAXIMUM_FAILED_LOGIN_ATTEMPTS:
            credential.locked_until = current_time + LOCKOUT_DURATION

        session.flush()

        raise AuthenticationFailedError("Invalid username or password.")

    credential.failed_login_count = 0
    credential.locked_until = None

    session.flush()

    return user
