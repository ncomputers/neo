import sqlalchemy as sa
from alembic import op

revision = "0015_menu_item_sort"
down_revision = "0014_i18n"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.add_column(
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("menu_items") as batch:
        batch.alter_column("sort", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("menu_items") as batch:
        batch.drop_column("sort")
