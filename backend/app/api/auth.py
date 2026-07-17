"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.domain.identity.authentication import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationFailedError,
)
from app.domain.identity.login import login_user
from app.models.user_credential import UserCredential
from app.schemas.auth import LoginRequest, LoginResponse, LoginUserResponse

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
        session.rollback()

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
