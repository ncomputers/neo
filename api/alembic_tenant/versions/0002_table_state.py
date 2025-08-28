"""add table state tracking columns

Revision ID: 0002_table_state
Revises: 0001_initial_tenant
Create Date: 2024-09-07
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002_table_state"
# Depends on alerts/outbox to keep chain ordered
down_revision: str | None = "0002_alerts_and_outbox"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("tables")}
    if "state" not in cols:
        op.add_column(
            "tables",
            sa.Column("state", sa.Text(), nullable=False, server_default="AVAILABLE"),
        )
    if "last_cleaned_at" not in cols:
        op.add_column(
            "tables",
            sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("tables")}
    if "last_cleaned_at" in cols:
        op.drop_column("tables", "last_cleaned_at")
    if "state" in cols:
        op.drop_column("tables", "state")
