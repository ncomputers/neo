#!/usr/bin/env python3
"""Run tenant-specific Alembic migrations.

This CLI generates a DSN for the provided tenant ID using either the
``--dsn-template`` option or the ``POSTGRES_TENANT_DSN_TEMPLATE`` environment
variable and executes ``alembic upgrade head`` against the tenant migration
environment. The template must contain a ``{tenant_id}`` placeholder, for
example::

    postgresql+asyncpg://u:p@host:5432/tenant_{tenant_id}

Either the flag or environment variable must be set before running migrations.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

TEMPLATE_ENV = "POSTGRES_TENANT_DSN_TEMPLATE"


def migrate(tenant_id: str, dsn_template: str | None = None) -> None:
    """Run Alembic migrations for ``tenant_id``."""
    template = dsn_template or os.getenv(TEMPLATE_ENV)
    if not template:
        raise RuntimeError(
            f"--dsn-template or {TEMPLATE_ENV} environment variable must be set"
        )
    try:
        dsn = template.format(tenant_id=tenant_id)
    except Exception as exc:  # pragma: no cover - invalid format string
        raise ValueError("Invalid DSN template") from exc
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
    parser.add_argument(
        "--dsn-template",
        help=f"DSN template for tenant databases (overrides {TEMPLATE_ENV})",
    )
    args = parser.parse_args()
    migrate(args.tenant, args.dsn_template)


if __name__ == "__main__":
    main()
