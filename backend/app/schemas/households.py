"""Household API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.household_membership import HouseholdRole


class HouseholdCreateRequest(BaseModel):
    """Payload for creating a household."""

    name: str = Field(min_length=1, max_length=150)


class HouseholdResponse(BaseModel):
    """Safe household information returned to a member."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_by_user_id: uuid.UUID
    created_at: datetime


class HouseholdListItem(HouseholdResponse):
    """Household summary with the current user's role."""

    role: HouseholdRole


class HouseholdMemberCreateRequest(BaseModel):
    """Payload for adding an existing user to a household."""

    username: str = Field(min_length=1, max_length=100)
    role: HouseholdRole


class HouseholdMemberResponse(BaseModel):
    """Safe household membership and user information."""

    membership_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: str
    role: HouseholdRole
    joined_at: datetime
