import sqlalchemy as sa
from alembic import op

revision = "0014_i18n"
down_revision = "0013_coupon_caps_windows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.add_column(sa.Column("name_i18n", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("desc_i18n", sa.JSON(), nullable=True))
    with op.batch_alter_table("tenant_meta") as batch:
        batch.add_column(
            sa.Column("default_lang", sa.String(), nullable=False, server_default="en")
        )
        batch.add_column(
            sa.Column(
                "enabled_langs", sa.JSON(), nullable=False, server_default='["en"]'
            )
        )
    with op.batch_alter_table("invoices") as batch:
        batch.add_column(sa.Column("bill_lang", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.drop_column("name_i18n")
        batch.drop_column("desc_i18n")
    with op.batch_alter_table("tenant_meta") as batch:
        batch.drop_column("default_lang")
        batch.drop_column("enabled_langs")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_column("bill_lang")
