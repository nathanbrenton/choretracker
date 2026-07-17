"""Tests for username normalization and validation."""

import pytest
from app.domain.identity.usernames import (
    InvalidUsernameError,
    normalize_username,
)


@pytest.mark.parametrize(
    ("raw_username", "expected"),
    [
        ("child_one", "child_one"),
        (" Child.One ", "child.one"),
        ("PARENT-01", "parent-01"),
        ("abc", "abc"),
    ],
)
def test_username_is_normalized(
    raw_username: str,
    expected: str,
) -> None:
    """Usernames should be trimmed and converted to lowercase."""

    assert normalize_username(raw_username) == expected


@pytest.mark.parametrize(
    "username",
    [
        "",
        "ab",
        "contains spaces",
        "child@example.com",
        "name!",
        "a" * 51,
    ],
)
def test_invalid_usernames_are_rejected(username: str) -> None:
    """Invalid username formats should raise a domain-specific error."""

    with pytest.raises(InvalidUsernameError):
        normalize_username(username)
