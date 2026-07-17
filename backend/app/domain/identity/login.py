"""Login orchestration for ChoreTracker users."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.identity.authentication import authenticate_user
from app.domain.identity.sessions import (
    DEFAULT_SESSION_LIFETIME,
    create_user_session,
)
from app.models.user import User
from app.models.user_session import UserSession


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Return the authenticated user and one-time plaintext session token."""

    user: User
    token: str
    session: UserSession


def login_user(
    session: Session,
    *,
    username: str,
    password: str,
    now: datetime | None = None,
    session_lifetime: timedelta = DEFAULT_SESSION_LIFETIME,
) -> LoginResult:
    """Authenticate a user and create a new server-managed session."""

    user = authenticate_user(
        session,
        username=username,
        password=password,
        now=now,
    )

    created_session = create_user_session(
        session,
        user_id=user.id,
        now=now,
        lifetime=session_lifetime,
    )

    return LoginResult(
        user=user,
        token=created_session.token,
        session=created_session.session,
    )
