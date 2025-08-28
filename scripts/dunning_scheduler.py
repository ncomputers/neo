#!/usr/bin/env python3
"""Compute dunning cohorts and log events.

This is a simplified scheduler that groups tenants based on subscription
expiry dates. It writes a ``dunning_events.json`` file with records to ensure
idempotency.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlencode

EVENT_LOG = Path("dunning_events.json")


def build_renew_url(plan: str, return_to: str, template_key: str) -> str:
    """Return deep link for the renew CTA with UTM tags."""
    params = {
        "plan": plan,
        "return_to": return_to,
        "utm_source": "dunning",
        "utm_campaign": template_key,
    }
    return "/admin/billing?" + urlencode(params)


@dataclass
class Tenant:
    id: str
    expires_at: date
    auto_renew: bool = False
    status: str = "ACTIVE"
    plan: str = "basic"
    updated_at: datetime | None = None
    channels: List[str] | None = None


class DunningScheduler:
    mapping = {7: "T-7", 3: "T-3", 1: "T-1", 0: "T+0", -3: "T+3", -7: "T+7"}

    def __init__(self, today: date | None = None):
        self.today = today or date.today()
        self.events = self._load_events()

    def _load_events(self) -> list[dict]:
        if EVENT_LOG.exists():
            return json.loads(EVENT_LOG.read_text())
        return []

    def _save_events(self) -> None:
        EVENT_LOG.write_text(json.dumps(self.events, indent=2))

    def _dedupe_key(self, tenant_id: str, template_key: str) -> str:
        return f"{tenant_id}:{template_key}:{self.today.isoformat()}"

    def _record(self, tenant_id: str, template_key: str, payload: dict) -> bool:
        key = self._dedupe_key(tenant_id, template_key)
        if any(evt["dedupe_key"] == key for evt in self.events):
            return False
        sha = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        self.events.append(
            {
                "tenant_id": tenant_id,
                "when": self.today.isoformat(),
                "template_key": template_key,
                "channels_sent": [],
                "dedupe_key": key,
                "payload_sha": sha,
            }
        )
        return True

    def _eligible(self, tenant: Tenant) -> bool:
        if tenant.auto_renew or tenant.status == "CANCELLED":
            return False
        if (
            tenant.updated_at
            and tenant.status == "ACTIVE"
            and datetime.utcnow() - tenant.updated_at < timedelta(hours=2)
        ):
            return False
        return True

    def run(self, tenants: Iterable[Tenant]) -> int:
        count = 0
        for t in tenants:
            if not self._eligible(t):
                continue
            days = (t.expires_at - self.today).days
            template_key = self.mapping.get(days)
            if template_key and self._record(t.id, template_key, {"plan": t.plan}):
                count += 1
        self._save_events()
        return count


def resolve_channels(settings, tenant: Tenant) -> list[str]:
    """Return enabled channels honouring tenant opt-outs."""
    opt_out = set(tenant.channels or [])
    channels: list[str] = []
    if getattr(settings, "dunning_email_enabled", True) and "email" not in opt_out:
        channels.append("email")
    if getattr(settings, "dunning_wa_enabled", False) and "wa" not in opt_out:
        channels.append("wa")
    return channels


async def main() -> int:
    # Placeholder tenants for manual runs
    tenants: list[Tenant] = []
    scheduler = DunningScheduler()
    return scheduler.run(tenants)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    asyncio.run(main())
