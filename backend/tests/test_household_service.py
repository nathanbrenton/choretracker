"""Integration tests for household domain services."""

import uuid

import pytest
from app.db.session import SessionLocal
from app.domain.households.service import (
    HouseholdAccessDeniedError,
    HouseholdMembershipAlreadyExistsError,
    InvalidHouseholdRoleError,
    add_household_member,
    create_household,
    get_household_membership,
    list_user_households,
)
from app.domain.identity.users import create_user
from app.models.household import Household
from app.models.household_membership import HouseholdRole
from app.models.user import User
from sqlalchemy import delete


def create_test_user(session, label: str) -> User:
    """Create a uniquely named user for one household test."""

    return create_user(
        session,
        username=f"{label}-{uuid.uuid4().hex}",
        display_name=label.title(),
    )


def test_create_household_creates_owner_membership() -> None:
    """The creator should become the household owner atomically."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        household = create_household(
            session,
            owner_user_id=owner.id,
            name="  The   Example   Home  ",
        )
        session.commit()

        membership = get_household_membership(
            session,
            household_id=household.id,
            user_id=owner.id,
        )

        assert household.name == "The Example Home"
        assert membership is not None
        assert membership.role == HouseholdRole.OWNER

        # Household deletion cascades through its memberships.
        session.execute(delete(Household).where(Household.id == household.id))
        session.execute(delete(User).where(User.id == owner.id))
        session.commit()


def test_owner_can_add_parent_and_child() -> None:
    """Owners should be able to add existing users in non-owner roles."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        parent = create_test_user(session, "parent")
        child = create_test_user(session, "child")
        household = create_household(
            session,
            owner_user_id=owner.id,
            name="Role Test Home",
        )

        parent_membership = add_household_member(
            session,
            household_id=household.id,
            actor_user_id=owner.id,
            target_username=parent.username,
            role=HouseholdRole.PARENT,
        )
        child_membership = add_household_member(
            session,
            household_id=household.id,
            actor_user_id=owner.id,
            target_username=child.username,
            role=HouseholdRole.CHILD,
        )
        session.commit()

        assert parent_membership.role == HouseholdRole.PARENT
        assert child_membership.role == HouseholdRole.CHILD

        # Remove the household before deleting its referenced users.
        session.execute(delete(Household).where(Household.id == household.id))
        session.execute(delete(User).where(User.id.in_([owner.id, parent.id, child.id])))
        session.commit()


def test_parent_can_add_child_but_not_parent() -> None:
    """Parents may add children but may not grant parent access."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        parent = create_test_user(session, "parent")
        child = create_test_user(session, "child")
        other_parent = create_test_user(session, "other-parent")
        household = create_household(
            session,
            owner_user_id=owner.id,
            name="Parent Rule Home",
        )
        add_household_member(
            session,
            household_id=household.id,
            actor_user_id=owner.id,
            target_username=parent.username,
            role=HouseholdRole.PARENT,
        )

        child_membership = add_household_member(
            session,
            household_id=household.id,
            actor_user_id=parent.id,
            target_username=child.username,
            role=HouseholdRole.CHILD,
        )

        with pytest.raises(HouseholdAccessDeniedError):
            add_household_member(
                session,
                household_id=household.id,
                actor_user_id=parent.id,
                target_username=other_parent.username,
                role=HouseholdRole.PARENT,
            )

        assert child_membership.role == HouseholdRole.CHILD
        session.rollback()


def test_child_cannot_add_members() -> None:
    """Child members must not manage household membership."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        child = create_test_user(session, "child")
        target = create_test_user(session, "target")
        household = create_household(
            session,
            owner_user_id=owner.id,
            name="Child Rule Home",
        )
        add_household_member(
            session,
            household_id=household.id,
            actor_user_id=owner.id,
            target_username=child.username,
            role=HouseholdRole.CHILD,
        )

        with pytest.raises(HouseholdAccessDeniedError):
            add_household_member(
                session,
                household_id=household.id,
                actor_user_id=child.id,
                target_username=target.username,
                role=HouseholdRole.CHILD,
            )

        session.rollback()


def test_duplicate_membership_and_owner_assignment_are_rejected() -> None:
    """Memberships are unique and owner assignment uses a separate future flow."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        child = create_test_user(session, "child")
        household = create_household(
            session,
            owner_user_id=owner.id,
            name="Constraint Home",
        )
        add_household_member(
            session,
            household_id=household.id,
            actor_user_id=owner.id,
            target_username=child.username,
            role=HouseholdRole.CHILD,
        )

        with pytest.raises(HouseholdMembershipAlreadyExistsError):
            add_household_member(
                session,
                household_id=household.id,
                actor_user_id=owner.id,
                target_username=child.username,
                role=HouseholdRole.CHILD,
            )

        other = create_test_user(session, "other")

        with pytest.raises(InvalidHouseholdRoleError):
            add_household_member(
                session,
                household_id=household.id,
                actor_user_id=owner.id,
                target_username=other.username,
                role=HouseholdRole.OWNER,
            )

        session.rollback()


def test_list_user_households_is_membership_scoped() -> None:
    """Users should see only households where they hold membership."""

    with SessionLocal() as session:
        owner = create_test_user(session, "owner")
        child = create_test_user(session, "child")
        first = create_household(
            session,
            owner_user_id=owner.id,
            name="First Home",
        )
        create_household(
            session,
            owner_user_id=child.id,
            name="Second Home",
        )
        add_household_member(
            session,
            household_id=first.id,
            actor_user_id=owner.id,
            target_username=child.username,
            role=HouseholdRole.CHILD,
        )
        session.commit()

        owner_households = list_user_households(session, user_id=owner.id)
        child_households = list_user_households(session, user_id=child.id)

        assert [household.name for household, _ in owner_households] == ["First Home"]
        assert {household.name for household, _ in child_households} == {
            "First Home",
            "Second Home",
        }

        session.rollback()
