"""monthly partitions for audit_log

Revision ID: 20250830_0000_audit_log_partitions
Revises: 20250829_0000_customer_consent_flags
Create Date: 2025-08-30
"""

import sqlalchemy as sa
from alembic import op

revision = "20250830_0000_audit_log_partitions"
down_revision = "20250829_0000_customer_consent_flags"
branch_labels = None
depends_on = None

_CREATE_PARTITIONS = """
CREATE TABLE IF NOT EXISTS audit_log_y2025m08
    PARTITION OF audit_log FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE IF NOT EXISTS audit_log_default
    PARTITION OF audit_log DEFAULT;
"""

_CREATE_TRIGGER = """
CREATE OR REPLACE FUNCTION audit_log_insert_trigger()
RETURNS TRIGGER AS $$
DECLARE
    _part text := 'audit_log_y' || to_char(NEW.created_at, 'YYYY') || 'm' || to_char(NEW.created_at, 'MM');
BEGIN
    EXECUTE format('INSERT INTO %I VALUES ($1.*)', _part) USING NEW;
    RETURN NULL;
EXCEPTION WHEN undefined_table THEN
    INSERT INTO audit_log_default VALUES (NEW.*);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_log_insert_router ON audit_log;
CREATE TRIGGER audit_log_insert_router
    BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_insert_trigger();
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_audit_log_y2025m08_tenant_id
    ON audit_log_y2025m08 (tenant_id);
"""

_DROP_INDEX = "DROP INDEX IF EXISTS idx_audit_log_y2025m08_tenant_id;"
_DROP_TRIGGER = """
DROP TRIGGER IF EXISTS audit_log_insert_router ON audit_log;
DROP FUNCTION IF EXISTS audit_log_insert_trigger();
"""
_DROP_PARTITIONS = """
DROP TABLE IF EXISTS audit_log_y2025m08;
DROP TABLE IF EXISTS audit_log_default;
"""


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        conn.execute(sa.text(_CREATE_PARTITIONS))
        conn.execute(sa.text(_CREATE_TRIGGER))
        conn.execute(sa.text(_CREATE_INDEX))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        conn.execute(sa.text(_DROP_INDEX))
        conn.execute(sa.text(_DROP_TRIGGER))
        conn.execute(sa.text(_DROP_PARTITIONS))
