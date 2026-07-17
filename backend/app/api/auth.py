"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.identity.authentication import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationFailedError,
)
from app.domain.identity.login import login_user
from app.domain.identity.sessions import (
    SessionNotFoundError,
    revoke_session,
)
from app.models.user import User
from app.models.user_credential import UserCredential
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LoginUserResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
) -> LoginResponse:
    """Authenticate a user and establish an HTTP-only session cookie."""

    settings = get_settings()

    try:
        result = login_user(
            session,
            username=payload.username,
            password=payload.password,
        )

        credential = session.scalar(
            select(UserCredential).where(UserCredential.user_id == result.user.id)
        )

        session.commit()
    except (
        AuthenticationFailedError,
        AccountDisabledError,
        AccountLockedError,
    ) as exc:
        # Persist failed-attempt counters and lockout timestamps while still
        # returning the same generic response for every authentication failure.
        session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc

    if credential is None:
        session.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=result.token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=int((result.session.expires_at - result.session.created_at).total_seconds()),
        path="/",
    )

    return LoginResponse(
        user=LoginUserResponse.model_validate(result.user),
        must_change_password=credential.must_change_password,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_authenticated_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Return safe information for the active authenticated user."""

    return CurrentUserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    response: Response,
    session: Annotated[Session, Depends(get_db_session)],
    session_token: Annotated[
        str | None,
        Cookie(alias="choretracker_session"),
    ] = None,
) -> Response:
    """Revoke the current session and clear its browser cookie."""

    settings = get_settings()

    if settings.auth_cookie_name != "choretracker_session":
        raise RuntimeError("Custom authentication cookie names are not yet supported.")

    if session_token is not None:
        try:
            revoke_session(
                session,
                token=session_token,
            )
            session.commit()
        except SessionNotFoundError:
            session.rollback()

    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT

    return response
