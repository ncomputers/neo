"""add table state tracking columns

Revision ID: 0002_table_state
Revises: 0001_initial_tenant
Create Date: 2024-09-07
"""

from alembic import op
import sqlalchemy as sa

revision: str = "0002_table_state"
down_revision: str | None = "0001_initial_tenant"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if not insp.has_column("tables", "state"):
        op.add_column(
            "tables",
            sa.Column("state", sa.Text(), nullable=False, server_default="AVAILABLE"),
        )
    if not insp.has_column("tables", "last_cleaned_at"):
        op.add_column(
            "tables",
            sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_column("tables", "last_cleaned_at"):
        op.drop_column("tables", "last_cleaned_at")
    if insp.has_column("tables", "state"):
        op.drop_column("tables", "state")
