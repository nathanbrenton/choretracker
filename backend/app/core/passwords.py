"""Password validation, hashing, and verification helpers."""

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

MINIMUM_PASSWORD_LENGTH = 12
MAXIMUM_PASSWORD_LENGTH = 256

password_hash = PasswordHash.recommended()


class InvalidPasswordError(ValueError):
    """Raised when a password violates ChoreTracker password rules."""


def validate_password(password: str) -> None:
    """Validate the initial ChoreTracker password-length policy."""

    password_length = len(password)

    if password_length < MINIMUM_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain at least {MINIMUM_PASSWORD_LENGTH} characters."
        )

    if password_length > MAXIMUM_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain no more than {MAXIMUM_PASSWORD_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    """Validate and hash a plaintext password using Argon2."""

    validate_password(password)

    return password_hash.hash(password)


def verify_password(
    password: str,
    encoded_hash: str,
) -> bool:
    """Return whether a plaintext password matches a stored hash."""

    try:
        return password_hash.verify(password, encoded_hash)
    except (TypeError, UnknownHashError, ValueError):
        return False
