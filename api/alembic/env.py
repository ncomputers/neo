from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from sqlalchemy.exc import NoSuchModuleError
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


def _coerce_sync_url(url: str) -> str:
    """Return a synchronous variant of an asyncpg DSN."""

    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg")
    return url


def _is_async_url(url: str) -> bool:
    """Return True if URL requests an async driver and it's available."""

    parsed = make_url(url)
    driver = parsed.drivername
    if driver.endswith("+asyncpg") or driver.endswith("+aiosqlite"):
        try:
            dialect = parsed.get_dialect()
        except NoSuchModuleError as exc:
            raise RuntimeError(
                "Async database driver not installed. Use SYNC_DATABASE_URL or install the async driver."
            ) from exc
        if not getattr(dialect, "is_async", False):
            raise RuntimeError(
                "Async URL resolved to a synchronous dialect. Use SYNC_DATABASE_URL or install the async driver."
            )
        return True
    return False


def run_migrations_offline() -> None:
    url = _coerce_sync_url(_get_url())
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode supporting async and sync URLs."""

    url = _get_url()
    configuration = {"sqlalchemy.url": url}
    if _is_async_url(url):
        connectable = async_engine_from_config(
            configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
        )
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn, target_metadata=target_metadata
                )
            )
            await connection.run_sync(lambda conn: context.run_migrations())
    else:
        connectable = engine_from_config(
            configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
        )
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
