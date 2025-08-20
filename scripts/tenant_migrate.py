#!/usr/bin/env python3
"""Run tenant-specific Alembic migrations.

This CLI generates a DSN for the provided tenant ID using the
``POSTGRES_TENANT_DSN_TEMPLATE`` environment variable and executes
``alembic upgrade head`` against the tenant migration environment.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from api.app.db.tenant import build_dsn

TEMPLATE_ENV = "POSTGRES_TENANT_DSN_TEMPLATE"


def migrate(tenant_id: str) -> None:
    """Run Alembic migrations for ``tenant_id``."""
    if not os.getenv(TEMPLATE_ENV):
        raise RuntimeError(f"{TEMPLATE_ENV} environment variable is not set")

    dsn = build_dsn(tenant_id)
    engine = create_async_engine(dsn)
    cfg = Config()
    cfg.set_main_option("script_location", "api/alembic_tenant")
    cfg.set_main_option("sqlalchemy.url", dsn)
    cfg.attributes["engine"] = engine
    try:
        command.upgrade(cfg, "head")
    finally:
        asyncio.run(engine.dispose())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run tenant migrations")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    args = parser.parse_args()
    migrate(args.tenant)


if __name__ == "__main__":
    main()
