from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy.engine import reflection
from sqlalchemy.ext.asyncio import AsyncEngine

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR.parent))

from app import models_tenant  # type: ignore  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = models_tenant.Base.metadata

# ``Inspector.has_column`` is missing on some SQLite versions shipped with
# SQLAlchemy; add a lightweight fallback so migrations can introspect columns
# consistently during tests.
if not hasattr(reflection.Inspector, "has_column"):

    def _has_column(self, table_name: str, column_name: str, schema: str | None = None) -> bool:  # type: ignore[override]
        return column_name in {c["name"] for c in self.get_columns(table_name, schema)}

    reflection.Inspector.has_column = _has_column  # type: ignore[attr-defined]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an AsyncEngine provided at runtime."""
    connectable: AsyncEngine | None = config.attributes.get("engine")
    if connectable is None:
        raise RuntimeError("Async engine missing from Alembic config")
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
