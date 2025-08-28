"""initial tenant

Revision ID: 0001_initial_tenant
Revises: None
Create Date: 2025-08-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_initial_tenant"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create the initial tenant schema with core tables."""

    op.create_table(
        "tenant_meta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("menu_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "menu_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("menu_categories.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "is_veg", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("gst_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("hsn_sac", sa.String(), nullable=True),
        sa.Column(
            "show_fssai", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "out_of_stock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("modifiers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("combos", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("dietary", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("allergens", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("qr_token", sa.String(), nullable=True, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="AVAILABLE"),
        sa.Column("width", sa.Integer(), nullable=True, server_default="80"),
        sa.Column("height", sa.Integer(), nullable=True, server_default="80"),
        sa.Column("shape", sa.String(12), nullable=True, server_default="rect"),
        sa.Column("zone", sa.String(64), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_group_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(), nullable=False, unique=True),
        sa.Column("bill_json", sa.JSON(), nullable=False),
        sa.Column("gst_breakup", sa.JSON(), nullable=True),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False, unique=True),
        sa.Column("percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("flat", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    """Drop core tables introduced in :func:`upgrade`."""

    op.drop_table("coupons")
    op.drop_table("invoices")
    op.drop_table("tables")
    op.drop_table("menu_items")
    op.drop_table("menu_categories")
    op.drop_table("tenant_meta")
