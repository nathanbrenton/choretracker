"""Reusable FastAPI request dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth_cookies import read_auth_cookie
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.identity.sessions import (
    SessionExpiredError,
    SessionNotFoundError,
    SessionRevokedError,
    get_active_session,
)
from app.models.user import User

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def get_current_user(
    request: Request,
    session: DatabaseSession,
) -> User:
    """Resolve the authenticated user from the configured session cookie."""

    settings = get_settings()
    session_token = read_auth_cookie(request, settings)

    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        user_session = get_active_session(
            session,
            token=session_token,
        )
    except (
        SessionExpiredError,
        SessionNotFoundError,
        SessionRevokedError,
    ) as exc:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        ) from exc

    user = session.get(User, user_session.user_id)

    if user is None:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    session.commit()

    return user
