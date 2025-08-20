"""create tenants table

Revision ID: 0001_create_tenants
Revises: None
Create Date: 2024-07-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_create_tenants"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("domain", sa.String(), unique=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("primary_color", sa.String(), nullable=True),
        sa.Column(
            "gst_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("invoice_prefix", sa.String(), nullable=True),
        sa.Column("ema_window", sa.Integer(), nullable=True),
        sa.Column("license_limits", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("tenants")
