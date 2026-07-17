"""Household membership model and role definitions."""

import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HouseholdRole(StrEnum):
    """Roles available within one household."""

    OWNER = "owner"
    PARENT = "parent"
    CHILD = "child"


class HouseholdMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Connect one user to one household with a household-scoped role."""

    __tablename__ = "household_memberships"
    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "user_id",
            name="uq_household_memberships_household_user",
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    role: Mapped[HouseholdRole] = mapped_column(
        Enum(
            HouseholdRole,
            name="household_role",
            native_enum=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )
