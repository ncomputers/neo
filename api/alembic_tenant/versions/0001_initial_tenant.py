"""initial tenant

Revision ID: 0001_initial_tenant
Revises: None
Create Date: 2025-08-20
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision: str = "0001_initial_tenant"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # will be autogen
    pass


def downgrade() -> None:
    # will be autogen
    pass
