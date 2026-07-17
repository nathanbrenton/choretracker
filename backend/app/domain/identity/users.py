"""User identity use cases."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.identity.usernames import normalize_username
from app.models.user import User


class UsernameAlreadyExistsError(ValueError):
    """Raised when a normalized username is already registered."""


def create_user(
    session: Session,
    *,
    username: str,
    display_name: str,
    is_developer: bool = False,
) -> User:
    """Create a user with normalized and validated identity fields."""

    normalized_username = normalize_username(username)
    normalized_display_name = display_name.strip()

    if not normalized_display_name:
        raise ValueError("Display name must not be empty.")

    existing_user = session.scalar(select(User).where(User.username == normalized_username))

    if existing_user is not None:
        raise UsernameAlreadyExistsError(f"Username {normalized_username!r} already exists.")

    user = User(
        username=normalized_username,
        display_name=normalized_display_name,
        is_developer=is_developer,
    )

    session.add(user)
    session.flush()

    return user
