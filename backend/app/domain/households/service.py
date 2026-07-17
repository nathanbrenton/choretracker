"""Household and membership use cases."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.identity.usernames import normalize_username
from app.models.household import Household
from app.models.household_membership import HouseholdMembership, HouseholdRole
from app.models.user import User, UserStatus

HOUSEHOLD_NAME_MAX_LENGTH = 150


class HouseholdNotFoundError(ValueError):
    """Raised when a household does not exist."""


class HouseholdAccessDeniedError(ValueError):
    """Raised when a user lacks access to a household operation."""


class HouseholdMemberNotFoundError(ValueError):
    """Raised when a target user does not exist or is unavailable."""


class HouseholdMembershipAlreadyExistsError(ValueError):
    """Raised when a user already belongs to a household."""


class InvalidHouseholdRoleError(ValueError):
    """Raised when a requested role cannot be assigned."""


def normalize_household_name(value: str) -> str:
    """Normalize and validate a household display name."""

    normalized = " ".join(value.split())

    if not normalized:
        raise ValueError("Household name must not be empty.")

    if len(normalized) > HOUSEHOLD_NAME_MAX_LENGTH:
        raise ValueError(f"Household name must not exceed {HOUSEHOLD_NAME_MAX_LENGTH} characters.")

    return normalized


def create_household(
    session: Session,
    *,
    owner_user_id: uuid.UUID,
    name: str,
) -> Household:
    """Create a household and its initial owner membership atomically."""

    owner = session.get(User, owner_user_id)

    if owner is None or owner.status != UserStatus.ACTIVE:
        raise HouseholdMemberNotFoundError("An active owner account is required.")

    household = Household(
        name=normalize_household_name(name),
        created_by_user_id=owner_user_id,
    )
    session.add(household)
    session.flush()

    session.add(
        HouseholdMembership(
            household_id=household.id,
            user_id=owner_user_id,
            role=HouseholdRole.OWNER,
        )
    )
    session.flush()

    return household


def get_household_membership(
    session: Session,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID,
) -> HouseholdMembership | None:
    """Return a user's membership in one household, when present."""

    return session.scalar(
        select(HouseholdMembership).where(
            HouseholdMembership.household_id == household_id,
            HouseholdMembership.user_id == user_id,
        )
    )


def list_user_households(
    session: Session,
    *,
    user_id: uuid.UUID,
) -> list[tuple[Household, HouseholdRole]]:
    """List households visible to a user together with their role."""

    rows = session.execute(
        select(Household, HouseholdMembership.role)
        .join(
            HouseholdMembership,
            HouseholdMembership.household_id == Household.id,
        )
        .where(HouseholdMembership.user_id == user_id)
        .order_by(Household.name, Household.id)
    ).all()

    return [(household, role) for household, role in rows]


def list_household_members(
    session: Session,
    *,
    household_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
) -> list[tuple[HouseholdMembership, User]]:
    """List members when the requesting user belongs to the household."""

    household = session.get(Household, household_id)

    if household is None:
        raise HouseholdNotFoundError("Household was not found.")

    if (
        get_household_membership(
            session,
            household_id=household_id,
            user_id=requesting_user_id,
        )
        is None
    ):
        raise HouseholdAccessDeniedError("Household access is required.")

    rows = session.execute(
        select(HouseholdMembership, User)
        .join(User, User.id == HouseholdMembership.user_id)
        .where(HouseholdMembership.household_id == household_id)
        .order_by(HouseholdMembership.created_at, HouseholdMembership.id)
    ).all()

    return [(membership, user) for membership, user in rows]


def add_household_member(
    session: Session,
    *,
    household_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    target_username: str,
    role: HouseholdRole,
) -> HouseholdMembership:
    """Add an existing active user under household-scoped role rules."""

    household = session.get(Household, household_id)

    if household is None:
        raise HouseholdNotFoundError("Household was not found.")

    actor_membership = get_household_membership(
        session,
        household_id=household_id,
        user_id=actor_user_id,
    )

    if actor_membership is None or actor_membership.role == HouseholdRole.CHILD:
        raise HouseholdAccessDeniedError("Parent or owner access is required.")

    if role == HouseholdRole.OWNER:
        raise InvalidHouseholdRoleError("Owner membership cannot be assigned here.")

    if actor_membership.role == HouseholdRole.PARENT and role != HouseholdRole.CHILD:
        raise HouseholdAccessDeniedError("Parents may add child members only.")

    username = normalize_username(target_username)
    target_user = session.scalar(select(User).where(User.username == username))

    if target_user is None or target_user.status != UserStatus.ACTIVE:
        raise HouseholdMemberNotFoundError("An active target user is required.")

    existing_membership = get_household_membership(
        session,
        household_id=household_id,
        user_id=target_user.id,
    )

    if existing_membership is not None:
        raise HouseholdMembershipAlreadyExistsError("The user already belongs to this household.")

    membership = HouseholdMembership(
        household_id=household_id,
        user_id=target_user.id,
        role=role,
    )
    session.add(membership)
    session.flush()

    return membership
