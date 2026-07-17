"""Tests for shared SQLAlchemy model conventions."""

import uuid
from datetime import datetime

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy.orm import Mapped, mapped_column


class ExampleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Temporary model used only to test shared conventions."""

    __tablename__ = "example_models"

    name: Mapped[str] = mapped_column(nullable=False)


def test_shared_model_uses_uuid_primary_key() -> None:
    """The shared primary key should generate UUID values."""

    id_column = ExampleModel.__table__.columns["id"]

    assert id_column.primary_key is True
    assert id_column.default is not None
    assert id_column.default.is_callable is True

    generated_value = id_column.default.arg(None)

    assert isinstance(generated_value, uuid.UUID)


def test_shared_model_defines_timestamp_columns() -> None:
    """Shared models should expose creation and update timestamps."""

    columns = ExampleModel.__table__.columns

    assert "created_at" in columns
    assert "updated_at" in columns
    assert columns["created_at"].type.timezone is True
    assert columns["updated_at"].type.timezone is True


def test_shared_timestamp_annotations_use_datetime() -> None:
    """Timestamp model annotations should remain datetime-based."""

    annotations = TimestampMixin.__annotations__

    assert annotations["created_at"] == Mapped[datetime]
    assert annotations["updated_at"] == Mapped[datetime]


def test_constraint_naming_convention_is_configured() -> None:
    """Database constraints should receive predictable names."""

    convention = Base.metadata.naming_convention

    assert convention["pk"] == "pk_%(table_name)s"
    assert convention["fk"] == ("fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s")
