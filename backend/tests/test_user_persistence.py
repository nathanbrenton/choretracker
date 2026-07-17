"""Integration tests for User persistence."""

import uuid

from app.db.session import SessionLocal
from app.models.user import User, UserStatus
from sqlalchemy import delete, select


def test_user_can_be_inserted_and_loaded() -> None:
    """A user should persist with UUID and database-backed defaults."""

    username = f"test-user-{uuid.uuid4()}"

    with SessionLocal() as session:
        user = User(
            username=username,
            display_name="Test User",
        )

        session.add(user)
        session.commit()

        user_id = user.id

        loaded_user = session.scalar(
            select(User).where(User.id == user_id),
        )

        assert loaded_user is not None
        assert loaded_user.id == user_id
        assert loaded_user.username == username
        assert loaded_user.display_name == "Test User"
        assert loaded_user.status == UserStatus.ACTIVE
        assert loaded_user.is_developer is False
        assert loaded_user.created_at is not None
        assert loaded_user.updated_at is not None

        session.execute(
            delete(User).where(User.id == user_id),
        )
        session.commit()
