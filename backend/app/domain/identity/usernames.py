"""Username normalization and validation rules."""

import re

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]+$")
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50


class InvalidUsernameError(ValueError):
    """Raised when a username violates ChoreTracker identity rules."""


def normalize_username(value: str) -> str:
    """Normalize and validate a case-insensitive login username."""

    normalized = value.strip().lower()

    if not USERNAME_MIN_LENGTH <= len(normalized) <= USERNAME_MAX_LENGTH:
        raise InvalidUsernameError(
            f"Username must be between {USERNAME_MIN_LENGTH} "
            f"and {USERNAME_MAX_LENGTH} characters."
        )

    if USERNAME_PATTERN.fullmatch(normalized) is None:
        raise InvalidUsernameError(
            "Username may contain only lowercase letters, numbers, "
            "periods, underscores, and hyphens."
        )

    return normalized
