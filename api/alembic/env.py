from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR.parent))

# Import models to register them with SQLAlchemy's metadata for Alembic.
import app.models_master  # type: ignore  # noqa: E402,F401
import app.models_tenant  # type: ignore  # noqa: E402,F401
from app.db import MasterBase, TenantBase  # type: ignore  # noqa: E402

from config import get_settings  # type: ignore  # noqa: E402

config = context.config
fileConfig(config.config_file_name)

settings = get_settings()
DB_URLS = {
    "master": settings.postgres_master_url,
    "tenant": settings.postgres_tenant_dsn_template.format(tenant_id="tenant"),
}

x_args = context.get_x_argument(as_dictionary=True)
target_metadata = (
    TenantBase.metadata if x_args.get("db") == "tenant" else MasterBase.metadata
)


def _get_url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args:
        return x_args["db_url"]
    return DB_URLS[x_args.get("db", "master")]


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""

    configuration = {"sqlalchemy.url": _get_url()}
    connectable = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn, target_metadata=target_metadata
            )
        )
        await connection.run_sync(context.run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
