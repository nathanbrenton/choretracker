"""Authentication API schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class LoginUserResponse(BaseModel):
    """Safe authenticated-user information returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    is_developer: bool


class LoginResponse(BaseModel):
    """Successful login response without the plaintext session token."""

    user: LoginUserResponse
    must_change_password: bool


class CurrentUserResponse(BaseModel):
    """Safe information about the currently authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    status: str
    is_developer: bool
