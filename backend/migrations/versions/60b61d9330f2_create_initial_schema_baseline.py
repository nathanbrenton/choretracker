"""create initial schema baseline

Revision ID: 60b61d9330f2
Revises:
Create Date: 2026-07-16 19:09:27.145603

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "60b61d9330f2"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
