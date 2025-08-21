"""add alerts rules and notifications outbox

Revision ID: 0002_alerts_and_outbox
Revises: 0001_initial_tenant
Create Date: 2024-08-18
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0002_alerts_and_outbox"
down_revision: str | None = "0001_initial_tenant"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_table(
        "notifications_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notifications_outbox")
    op.drop_table("alerts_rules")
