"""Password credential use cases."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.models.user import User
from app.models.user_credential import UserCredential


class UserNotFoundError(ValueError):
    """Raised when credential work targets a missing user."""


class CredentialAlreadyExistsError(ValueError):
    """Raised when attempting to create a second credential for one user."""


class CredentialNotFoundError(ValueError):
    """Raised when attempting to update a missing credential."""


def create_user_credential(
    session: Session,
    *,
    user_id: uuid.UUID,
    password: str,
    must_change_password: bool = False,
) -> UserCredential:
    """Create the initial password credential for an existing user."""

    user = session.get(User, user_id)

    if user is None:
        raise UserNotFoundError(f"User {user_id} does not exist.")

    existing_credential = session.get(UserCredential, user_id)

    if existing_credential is not None:
        raise CredentialAlreadyExistsError(f"User {user_id} already has a password credential.")

    credential = UserCredential(
        user_id=user_id,
        password_hash=hash_password(password),
        password_changed_at=datetime.now(UTC),
        must_change_password=must_change_password,
    )

    session.add(credential)
    session.flush()

    return credential


def replace_user_password(
    session: Session,
    *,
    user_id: uuid.UUID,
    password: str,
    must_change_password: bool = False,
) -> UserCredential:
    """Replace a user's password and clear temporary lockout state."""

    credential = session.scalar(select(UserCredential).where(UserCredential.user_id == user_id))

    if credential is None:
        raise CredentialNotFoundError(f"User {user_id} does not have a password credential.")

    credential.password_hash = hash_password(password)
    credential.password_changed_at = datetime.now(UTC)
    credential.must_change_password = must_change_password
    credential.failed_login_count = 0
    credential.locked_until = None

    session.flush()

    return credential
