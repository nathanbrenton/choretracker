"""Tests for password hashing and verification."""

import pytest
from app.core.passwords import (
    MAXIMUM_PASSWORD_LENGTH,
    MINIMUM_PASSWORD_LENGTH,
    InvalidPasswordError,
    hash_password,
    validate_password,
    verify_password,
)


def test_password_is_hashed_with_argon2() -> None:
    """Stored password values should be Argon2 hashes, not plaintext."""

    plaintext = "correct horse battery staple"
    encoded_hash = hash_password(plaintext)

    assert encoded_hash != plaintext
    assert encoded_hash.startswith("$argon2")
    assert verify_password(plaintext, encoded_hash) is True


def test_incorrect_password_is_rejected() -> None:
    """Verification should reject a password that does not match."""

    encoded_hash = hash_password("correct horse battery staple")

    assert verify_password("incorrect password value", encoded_hash) is False


def test_same_password_receives_unique_salts() -> None:
    """Repeated hashing should not produce identical stored values."""

    plaintext = "correct horse battery staple"

    first_hash = hash_password(plaintext)
    second_hash = hash_password(plaintext)

    assert first_hash != second_hash
    assert verify_password(plaintext, first_hash) is True
    assert verify_password(plaintext, second_hash) is True


@pytest.mark.parametrize(
    "password",
    [
        "",
        "short",
        "a" * (MINIMUM_PASSWORD_LENGTH - 1),
    ],
)
def test_short_passwords_are_rejected(password: str) -> None:
    """Passwords below the minimum length should be rejected."""

    with pytest.raises(InvalidPasswordError, match="at least"):
        validate_password(password)


def test_maximum_password_length_is_accepted() -> None:
    """A password at the maximum length should remain valid."""

    validate_password("a" * MAXIMUM_PASSWORD_LENGTH)


def test_overly_long_password_is_rejected() -> None:
    """Unbounded password input should be rejected before hashing."""

    with pytest.raises(InvalidPasswordError, match="no more than"):
        validate_password("a" * (MAXIMUM_PASSWORD_LENGTH + 1))


def test_malformed_hash_is_rejected_safely() -> None:
    """Malformed stored values should not escape as authentication errors."""

    assert verify_password("correct horse battery staple", "not-a-valid-hash") is False
