#!/usr/bin/env python3
"""Purge tenants whose ``purge_at`` has passed."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "api"))
sys.path.append(str(BASE_DIR / "scripts"))

from app.db.master import (  # type: ignore  # noqa: E402
    get_session as get_master_session,
)
from app.models_master import Tenant  # type: ignore  # noqa: E402
from retention_enforce import enforce  # type: ignore  # noqa: E402


async def purge_due() -> None:
    """Anonymize and purge tenants scheduled for deletion."""

    now = datetime.utcnow()
    async with get_master_session() as session:
        result = await session.scalars(
            select(Tenant).where(
                Tenant.purge_at.isnot(None),
                Tenant.purge_at <= now,
            )
        )
        tenants = list(result)
        for tenant in tenants:
            await enforce(tenant.name)
            tenant.name = f"purged-{tenant.id}"
            tenant.domain = None
            tenant.status = "purged"
            tenant.closed_at = None
            tenant.purge_at = None
        if tenants:
            await session.commit()


def main() -> None:
    asyncio.run(purge_due())


if __name__ == "__main__":
    main()
