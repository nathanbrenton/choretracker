"""Integration tests for password credential use cases."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.passwords import verify_password
from app.db.session import SessionLocal
from app.domain.identity.credentials import (
    CredentialAlreadyExistsError,
    CredentialNotFoundError,
    UserNotFoundError,
    create_user_credential,
    replace_user_password,
)
from app.domain.identity.users import create_user
from app.models.user import User
from sqlalchemy import delete


def test_create_user_credential_hashes_password() -> None:
    """Credential creation should persist an Argon2 hash, not plaintext."""

    username = f"credential-user-{uuid.uuid4().hex}"
    plaintext = "correct horse battery staple"

    with SessionLocal() as session:
        user = create_user(
            session,
            username=username,
            display_name="Credential User",
        )

        credential = create_user_credential(
            session,
            user_id=user.id,
            password=plaintext,
            must_change_password=True,
        )
        session.commit()

        user_id = user.id

        assert credential.user_id == user_id
        assert credential.password_hash != plaintext
        assert credential.password_hash.startswith("$argon2")
        assert verify_password(plaintext, credential.password_hash) is True
        assert credential.must_change_password is True
        assert credential.failed_login_count == 0
        assert credential.locked_until is None
        assert credential.password_changed_at.tzinfo is not None

        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_create_user_credential_rejects_missing_user() -> None:
    """Credentials must not be created for an unknown user."""

    with SessionLocal() as session, pytest.raises(UserNotFoundError):
        create_user_credential(
            session,
            user_id=uuid.uuid4(),
            password="correct horse battery staple",
        )


def test_create_user_credential_rejects_duplicate() -> None:
    """A user should have no more than one password credential."""

    username = f"dupcred-{uuid.uuid4().hex}"

    with SessionLocal() as session:
        user = create_user(
            session,
            username=username,
            display_name="Duplicate Credential User",
        )

        create_user_credential(
            session,
            user_id=user.id,
            password="correct horse battery staple",
        )
        session.commit()

        user_id = user.id

        with pytest.raises(CredentialAlreadyExistsError):
            create_user_credential(
                session,
                user_id=user_id,
                password="another secure password value",
            )

        session.rollback()
        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_replace_user_password_updates_security_state() -> None:
    """Replacing a password should clear failures and temporary lockout."""

    username = f"replace-password-{uuid.uuid4().hex}"
    original_password = "correct horse battery staple"
    replacement_password = "a different secure password"

    with SessionLocal() as session:
        user = create_user(
            session,
            username=username,
            display_name="Password Replacement User",
        )

        credential = create_user_credential(
            session,
            user_id=user.id,
            password=original_password,
        )
        session.commit()

        user_id = user.id
        original_changed_at = credential.password_changed_at

        credential.failed_login_count = 4
        credential.locked_until = datetime.now(UTC) + timedelta(minutes=30)
        session.commit()

        updated_credential = replace_user_password(
            session,
            user_id=user_id,
            password=replacement_password,
            must_change_password=True,
        )
        session.commit()

        assert verify_password(
            replacement_password,
            updated_credential.password_hash,
        )
        assert not verify_password(
            original_password,
            updated_credential.password_hash,
        )
        assert updated_credential.password_changed_at >= original_changed_at
        assert updated_credential.must_change_password is True
        assert updated_credential.failed_login_count == 0
        assert updated_credential.locked_until is None

        session.execute(delete(User).where(User.id == user_id))
        session.commit()


def test_replace_user_password_rejects_missing_credential() -> None:
    """Password replacement requires an existing credential row."""

    username = f"nocred-{uuid.uuid4().hex}"

    with SessionLocal() as session:
        user = create_user(
            session,
            username=username,
            display_name="Missing Credential User",
        )
        session.commit()

        user_id = user.id

        with pytest.raises(CredentialNotFoundError):
            replace_user_password(
                session,
                user_id=user_id,
                password="correct horse battery staple",
            )

        session.execute(delete(User).where(User.id == user_id))
        session.commit()
