"""Helpers for ChoreTracker authentication cookies."""

from fastapi import Request, Response

from app.core.config import Settings


def read_auth_cookie(
    request: Request,
    settings: Settings,
) -> str | None:
    """Read the configured authentication cookie from a request."""

    return request.cookies.get(settings.auth_cookie_name)


def set_auth_cookie(
    response: Response,
    *,
    settings: Settings,
    token: str,
    max_age: int,
) -> None:
    """Set the opaque authentication token as an HTTP-only cookie."""

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def clear_auth_cookie(
    response: Response,
    *,
    settings: Settings,
) -> None:
    """Clear the configured authentication cookie."""

    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
