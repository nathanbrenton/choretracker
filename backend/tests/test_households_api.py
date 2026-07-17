"""End-to-end API tests for household creation and membership."""

import uuid

from app.db.session import SessionLocal
from app.domain.identity.credentials import create_user_credential
from app.domain.identity.users import create_user
from app.main import app
from app.models.household import Household
from app.models.household_membership import HouseholdMembership
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import delete

TEST_PASSWORD = "correct horse battery staple"


def create_api_user(label: str) -> tuple[str, uuid.UUID]:
    """Create one authenticated-test identity."""

    with SessionLocal() as session:
        user = create_user(
            session,
            username=f"{label}-{uuid.uuid4().hex}",
            display_name=label.title(),
        )
        create_user_credential(
            session,
            user_id=user.id,
            password=TEST_PASSWORD,
        )
        session.commit()
        return user.username, user.id


def login(client: TestClient, username: str) -> None:
    """Authenticate one test client."""

    response = client.post(
        "/auth/login",
        json={"username": username, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200


def delete_users(*user_ids: uuid.UUID) -> None:
    """Delete temporary household data and API users in dependency order."""

    with SessionLocal() as session:
        # Delete households created by these users first.
        # Memberships cascade from household deletion.
        session.execute(delete(Household).where(Household.created_by_user_id.in_(user_ids)))

        # Remove any remaining memberships for these users.
        session.execute(
            delete(HouseholdMembership).where(HouseholdMembership.user_id.in_(user_ids))
        )

        session.execute(delete(User).where(User.id.in_(user_ids)))
        session.commit()


def test_household_api_owner_parent_child_flow() -> None:
    """Create, list, inspect, and populate a household through the API."""

    owner_username, owner_id = create_api_user("api-owner")
    parent_username, parent_id = create_api_user("api-parent")
    child_username, child_id = create_api_user("api-child")
    owner_client = TestClient(app)
    parent_client = TestClient(app)

    try:
        login(owner_client, owner_username)
        create_response = owner_client.post(
            "/households",
            json={"name": "  API   Household  "},
        )

        assert create_response.status_code == 201
        assert create_response.json()["name"] == "API Household"
        household_id = create_response.json()["id"]

        list_response = owner_client.get("/households")
        assert list_response.status_code == 200
        assert list_response.json()[0]["role"] == "owner"

        parent_response = owner_client.post(
            f"/households/{household_id}/members",
            json={"username": parent_username, "role": "parent"},
        )
        child_response = owner_client.post(
            f"/households/{household_id}/members",
            json={"username": child_username, "role": "child"},
        )

        assert parent_response.status_code == 201
        assert child_response.status_code == 201

        members_response = owner_client.get(f"/households/{household_id}/members")
        assert members_response.status_code == 200
        assert {member["role"] for member in members_response.json()} == {
            "owner",
            "parent",
            "child",
        }

        login(parent_client, parent_username)
        parent_households = parent_client.get("/households")
        assert parent_households.status_code == 200
        assert parent_households.json()[0]["role"] == "parent"
    finally:
        owner_client.cookies.clear()
        parent_client.cookies.clear()
        delete_users(owner_id, parent_id, child_id)


def test_household_api_requires_authentication() -> None:
    """Household endpoints should reject anonymous requests."""

    client = TestClient(app)

    assert client.get("/households").status_code == 401
    assert client.post("/households", json={"name": "Nope"}).status_code == 401


def test_child_cannot_manage_membership() -> None:
    """A child may view a household but may not add another member."""

    owner_username, owner_id = create_api_user("owner")
    child_username, child_id = create_api_user("child")
    target_username, target_id = create_api_user("target")
    owner_client = TestClient(app)
    child_client = TestClient(app)

    try:
        login(owner_client, owner_username)
        household_id = owner_client.post(
            "/households",
            json={"name": "Protected Home"},
        ).json()["id"]
        owner_client.post(
            f"/households/{household_id}/members",
            json={"username": child_username, "role": "child"},
        )

        login(child_client, child_username)
        response = child_client.post(
            f"/households/{household_id}/members",
            json={"username": target_username, "role": "child"},
        )

        assert response.status_code == 403
        assert child_client.get(f"/households/{household_id}").status_code == 200
    finally:
        owner_client.cookies.clear()
        child_client.cookies.clear()
        delete_users(owner_id, child_id, target_id)
