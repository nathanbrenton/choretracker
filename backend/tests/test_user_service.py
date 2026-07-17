"""Integration tests for user identity use cases."""

import uuid

import pytest
from app.db.session import SessionLocal
from app.domain.identity.users import (
    UsernameAlreadyExistsError,
    create_user,
)
from app.models.user import User
from sqlalchemy import delete


def test_create_user_normalizes_identity_fields() -> None:
    """User creation should normalize usernames and trim display names."""

    raw_username = f" Parent_{uuid.uuid4().hex} "

    with SessionLocal() as session:
        user = create_user(
            session,
            username=raw_username,
            display_name="  Example Parent  ",
        )
        session.commit()

        user_id = user.id

        assert user.username == raw_username.strip().lower()
        assert user.display_name == "Example Parent"
        assert user.is_developer is False

        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_create_user_rejects_duplicate_normalized_username() -> None:
    """Case and whitespace changes must not bypass uniqueness checks."""

    base_username = f"child_{uuid.uuid4().hex}"

    with SessionLocal() as session:
        first_user = create_user(
            session,
            username=base_username,
            display_name="First Child",
        )
        session.commit()

        with pytest.raises(UsernameAlreadyExistsError):
            create_user(
                session,
                username=f"  {base_username.upper()}  ",
                display_name="Second Child",
            )

        session.rollback()

        session.execute(
            delete(User).where(User.id == first_user.id),
        )
        session.commit()


def test_create_user_rejects_blank_display_name() -> None:
    """A user must have a non-empty display name."""

    with SessionLocal() as session, pytest.raises(ValueError, match="Display name"):
        create_user(
            session,
            username=f"user_{uuid.uuid4().hex}",
            display_name="   ",
        )


def test_create_user_can_mark_developer_account() -> None:
    """Developer access should be assigned only when explicitly requested."""

    username = f"developer_{uuid.uuid4().hex}"

    with SessionLocal() as session:
        user = create_user(
            session,
            username=username,
            display_name="Development Operator",
            is_developer=True,
        )
        session.commit()

        user_id = user.id

        assert user.is_developer is True

        session.execute(delete(User).where(User.id == user_id))
        session.commit()
