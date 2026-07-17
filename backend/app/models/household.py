"""Household model for ChoreTracker."""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Household(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A household that groups people, chores, and simulated allowances."""

    __tablename__ = "households"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
