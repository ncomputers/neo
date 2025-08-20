"""Utilities for tenant-specific database engines.

The DSN template is read from the ``POSTGRES_TENANT_DSN_TEMPLATE`` environment
variable and is expected to include a ``{tenant_id}`` placeholder. For example::

    postgresql+asyncpg://u:p@host:5432/tenant_{tenant_id}
    postgresql://other:secret@localhost/tenant_{tenant_id}

Use :func:`build_dsn` to render a DSN for a tenant and :func:`get_engine` to
create an :class:`~sqlalchemy.ext.asyncio.AsyncEngine` for it.
"""

from __future__ import annotations

import os
from typing import Final

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

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
    return create_async_engine(dsn)


__all__ = ["build_dsn", "get_engine"]
