"""Tests for the initial ChoreTracker project structure."""

import app


def test_backend_package_is_importable() -> None:
    """The backend application package should import successfully."""
    assert app is not None
