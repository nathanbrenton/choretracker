"""Server-managed authentication session use cases."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession

DEFAULT_SESSION_LIFETIME = timedelta(hours=12)
SESSION_TOKEN_BYTES = 32


class SessionNotFoundError(ValueError):
    """Raised when a session token does not identify a stored session."""


class SessionExpiredError(ValueError):
    """Raised when a stored session has expired."""


class SessionRevokedError(ValueError):
    """Raised when a stored session has been revoked."""


class UserNotFoundError(ValueError):
    """Raised when a session targets a missing user."""


@dataclass(frozen=True, slots=True)
class CreatedSession:
    """Return the plaintext token once alongside its persisted session."""

    token: str
    session: UserSession


def generate_session_token() -> str:
    """Generate a cryptographically secure opaque session token."""

    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Return the stable SHA-256 hash stored in PostgreSQL."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(
    session: Session,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
    lifetime: timedelta = DEFAULT_SESSION_LIFETIME,
) -> CreatedSession:
    """Create a revocable server-managed session for an existing user."""

    current_time = now or datetime.now(UTC)

    user = session.get(User, user_id)

    if user is None:
        raise UserNotFoundError(f"User {user_id} does not exist.")

    token = generate_session_token()

    user_session = UserSession(
        user_id=user_id,
        token_hash=hash_session_token(token),
        expires_at=current_time + lifetime,
    )

    session.add(user_session)
    session.flush()

    return CreatedSession(
        token=token,
        session=user_session,
    )


def get_active_session(
    session: Session,
    *,
    token: str,
    now: datetime | None = None,
    update_last_used: bool = True,
) -> UserSession:
    """Resolve an active session from its plaintext token."""

    current_time = now or datetime.now(UTC)
    token_hash = hash_session_token(token)

    user_session = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))

    if user_session is None:
        raise SessionNotFoundError("Session was not found.")

    if user_session.revoked_at is not None:
        raise SessionRevokedError("Session has been revoked.")

    if user_session.expires_at <= current_time:
        raise SessionExpiredError("Session has expired.")

    if update_last_used:
        user_session.last_used_at = current_time
        session.flush()

    return user_session


def revoke_session(
    session: Session,
    *,
    token: str,
    now: datetime | None = None,
) -> UserSession:
    """Revoke one stored session identified by its plaintext token."""

    current_time = now or datetime.now(UTC)
    token_hash = hash_session_token(token)

    user_session = session.scalar(select(UserSession).where(UserSession.token_hash == token_hash))

    if user_session is None:
        raise SessionNotFoundError("Session was not found.")

    if user_session.revoked_at is None:
        user_session.revoked_at = current_time
        session.flush()

    return user_session
