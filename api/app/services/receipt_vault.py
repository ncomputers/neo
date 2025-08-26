"""Guest receipt vault stored in Redis.

Receipts are persisted only when guests share their contact details and
explicitly consent. Each contact key retains up to the last ten receipts with
an expiry configured via ``guest_receipts_ttl_days``.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from config import get_settings


def redact_invoice(invoice: dict) -> dict:
    """Return a redacted copy of ``invoice`` removing sensitive fields.

    The current implementation strips the tax breakdown to avoid exposing line
    level details while preserving the overall totals.
    """

    redacted = dict(invoice)
    redacted.pop("tax_breakup", None)
    return redacted


class ReceiptVault:
    """Lightweight wrapper around Redis for storing guest receipts."""

    def __init__(self, redis) -> None:
        self.redis = redis
        self.ttl_secs = get_settings().guest_receipts_ttl_days * 86400

    async def add(self, contact: str, invoice: dict) -> None:
        """Push a redacted ``invoice`` for ``contact`` with configured TTL."""

        key = f"receipts:{contact}"
        await self.redis.lpush(key, json.dumps(redact_invoice(invoice)))
        await self.redis.ltrim(key, 0, 9)
        await self.redis.expire(key, self.ttl_secs)

    async def list(self, contact: str) -> Iterable[dict[str, Any]]:
        """Return up to the last ten receipts for ``contact``."""

        key = f"receipts:{contact}"
        data = await self.redis.lrange(key, 0, 9)
        return [json.loads(d) for d in data]


__all__ = ["ReceiptVault", "redact_invoice"]
