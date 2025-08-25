#!/usr/bin/env python3
"""Apply tenant-specific data retention policies."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from sqlalchemy import select

# Ensure ``api`` package is importable when running as a standalone script
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))
sys.path.append(str(BASE_DIR / "scripts"))

from app.db.master import get_session as get_master_session  # type: ignore  # noqa: E402
from app.models_master import Tenant  # type: ignore  # noqa: E402
from anonymize_pii import anonymize  # type: ignore  # noqa: E402
from retention_sweep import sweep  # type: ignore  # noqa: E402


async def enforce(tenant_name: str) -> None:
    """Apply retention settings for ``tenant_name``."""

    async with get_master_session() as session:
        tenant = await session.scalar(select(Tenant).where(Tenant.name == tenant_name))
    if tenant is None:
        raise ValueError(f"Unknown tenant: {tenant_name}")

    tenant_id = str(tenant.id)

    if tenant.retention_days_customers:
        await anonymize(tenant_id, tenant.retention_days_customers)
    if tenant.retention_days_outbox:
        await sweep(tenant_id, tenant.retention_days_outbox)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Enforce tenant retention policy")
    parser.add_argument("--tenant", required=True, help="Tenant name")
    args = parser.parse_args()
    asyncio.run(enforce(args.tenant))


if __name__ == "__main__":
    _cli()
