"""Utilities for tenant-specific database engines.

The DSN template is read from the ``POSTGRES_TENANT_DSN_TEMPLATE`` environment
variable and is expected to include a ``{tenant_id}`` placeholder. For example::

    postgresql+asyncpg://u:p@host:5432/tenant_{tenant_id}

Use :func:`build_dsn` to render a DSN for a tenant and :func:`get_engine` to
create an :class:`~sqlalchemy.ext.asyncio.AsyncEngine` for it.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Final

from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.app.obs import add_query_logger

TEMPLATE_ENV: Final[str] = "POSTGRES_TENANT_DSN_TEMPLATE"


def build_dsn(tenant_id: str) -> str:
    """Return a DSN for ``tenant_id`` based on ``POSTGRES_TENANT_DSN_TEMPLATE``.

    Parameters
    ----------
    tenant_id:
        Identifier of the tenant used to substitute ``{tenant_id}`` in the
        template.
    """
    template = os.getenv(TEMPLATE_ENV)
    if not template:
        raise RuntimeError(f"{TEMPLATE_ENV} environment variable is not set")
    try:
        return template.format(tenant_id=tenant_id)
    except Exception as exc:  # pragma: no cover - invalid format string
        raise ValueError("Invalid DSN template") from exc


def get_engine(tenant_id: str) -> AsyncEngine:
    """Create and return an :class:`AsyncEngine` for ``tenant_id``.

    The returned engine is created using
    :func:`sqlalchemy.ext.asyncio.create_async_engine`.
    """
    dsn = build_dsn(tenant_id)
    engine = create_async_engine(dsn)
    add_query_logger(engine, tenant_id)
    return engine


@asynccontextmanager
async def get_tenant_session(
    tenant_id: str,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an :class:`AsyncSession` bound to ``tenant_id``'s engine."""

    engine = get_engine(tenant_id)
    Session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = Session()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def run_tenant_migrations(tenant_id: str) -> None:
    """Run Alembic migrations for ``tenant_id``.

    This uses the programmatic Alembic API mirroring the
    ``scripts/tenant_migrate.py`` helper.
    """

    logger = logging.getLogger(__name__)

    engine: AsyncEngine | None = None
    try:
        dsn = build_dsn(tenant_id)
        engine = create_async_engine(dsn)

        cfg = Config()
        cfg.set_main_option(
            "script_location",
            str(Path(__file__).resolve().parents[2] / "alembic_tenant"),
        )
        cfg.set_main_option("sqlalchemy.url", dsn)
        cfg.attributes["engine"] = engine

        await asyncio.to_thread(command.upgrade, cfg, "head")
    except Exception as exc:  # pragma: no cover - runtime errors
        logger.error("Failed to run migrations for %s: %s", tenant_id, exc)
        raise
    finally:
        if engine is not None:
            await engine.dispose()


__all__ = [
    "build_dsn",
    "get_engine",
    "get_tenant_session",
    "run_tenant_migrations",
]
