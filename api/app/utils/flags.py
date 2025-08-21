from __future__ import annotations

"""Feature flag utilities."""

from typing import Any
from ..db.master import get_session
from ..models_master import Tenant


async def can_use(tenant_id: str, flag: str) -> bool:
    """Return True if ``flag`` is enabled for ``tenant_id``."""
    async with get_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            return False
        flags: dict[str, Any] = tenant.flags or {}
        return bool(flags.get(flag))
