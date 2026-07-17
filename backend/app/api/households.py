"""Household API routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import DatabaseSession, get_current_user
from app.domain.households.service import (
    HouseholdAccessDeniedError,
    HouseholdMemberNotFoundError,
    HouseholdMembershipAlreadyExistsError,
    HouseholdNotFoundError,
    InvalidHouseholdRoleError,
    add_household_member,
    create_household,
    get_household_membership,
    list_household_members,
    list_user_households,
)
from app.models.household import Household
from app.models.user import User
from app.schemas.households import (
    HouseholdCreateRequest,
    HouseholdListItem,
    HouseholdMemberCreateRequest,
    HouseholdMemberResponse,
    HouseholdResponse,
)

router = APIRouter(
    prefix="/households",
    tags=["households"],
)

CurrentUser = Annotated[User, Depends(get_current_user)]


def household_response(household: Household) -> HouseholdResponse:
    """Convert a household model into its API representation."""

    return HouseholdResponse.model_validate(household)


@router.post(
    "",
    response_model=HouseholdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_household_endpoint(
    payload: HouseholdCreateRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> HouseholdResponse:
    """Create a household owned by the authenticated user."""

    household = create_household(
        session,
        owner_user_id=current_user.id,
        name=payload.name,
    )
    session.commit()
    session.refresh(household)

    return household_response(household)


@router.get(
    "",
    response_model=list[HouseholdListItem],
)
def list_households_endpoint(
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[HouseholdListItem]:
    """List every household visible to the authenticated user."""

    return [
        HouseholdListItem(
            **household_response(household).model_dump(),
            role=role,
        )
        for household, role in list_user_households(
            session,
            user_id=current_user.id,
        )
    ]


@router.get(
    "/{household_id}",
    response_model=HouseholdListItem,
)
def get_household_endpoint(
    household_id: uuid.UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> HouseholdListItem:
    """Return one household when the current user is a member."""

    household = session.get(Household, household_id)
    membership = get_household_membership(
        session,
        household_id=household_id,
        user_id=current_user.id,
    )

    if household is None or membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household was not found.",
        )

    return HouseholdListItem(
        **household_response(household).model_dump(),
        role=membership.role,
    )


@router.get(
    "/{household_id}/members",
    response_model=list[HouseholdMemberResponse],
)
def list_members_endpoint(
    household_id: uuid.UUID,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> list[HouseholdMemberResponse]:
    """List users belonging to a household."""

    try:
        rows = list_household_members(
            session,
            household_id=household_id,
            requesting_user_id=current_user.id,
        )
    except (HouseholdNotFoundError, HouseholdAccessDeniedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household was not found.",
        ) from exc

    return [
        HouseholdMemberResponse(
            membership_id=membership.id,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=membership.role,
            joined_at=membership.created_at,
        )
        for membership, user in rows
    ]


@router.post(
    "/{household_id}/members",
    response_model=HouseholdMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member_endpoint(
    household_id: uuid.UUID,
    payload: HouseholdMemberCreateRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> HouseholdMemberResponse:
    """Add an existing active user to a household."""

    try:
        membership = add_household_member(
            session,
            household_id=household_id,
            actor_user_id=current_user.id,
            target_username=payload.username,
            role=payload.role,
        )
        target_user = session.get(User, membership.user_id)
        session.commit()
        session.refresh(membership)
    except HouseholdNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household was not found.",
        ) from exc
    except HouseholdAccessDeniedError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Household management access is required.",
        ) from exc
    except HouseholdMemberNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found.",
        ) from exc
    except HouseholdMembershipAlreadyExistsError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already belongs to this household.",
        ) from exc
    except InvalidHouseholdRoleError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if target_user is None:
        raise RuntimeError("Membership target disappeared during creation.")

    return HouseholdMemberResponse(
        membership_id=membership.id,
        user_id=target_user.id,
        username=target_user.username,
        display_name=target_user.display_name,
        role=membership.role,
        joined_at=membership.created_at,
    )
