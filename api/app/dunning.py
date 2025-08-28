from __future__ import annotations

"""Helpers for subscription dunning and renewal links."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import quote
import json
import os

TEMPLATE_OFFSETS = {
    7: "T-7",
    3: "T-3",
    1: "T-1",
    0: "T+0",
    -3: "T+3",
    -7: "T+7",
}


def compute_template_key(expiry: date, today: date | None = None) -> Optional[str]:
    """Return template key for the given expiry date.

    Args:
        expiry: Subscription expiry date.
        today: Reference date (defaults to ``date.today()``).
    """
    today = today or date.today()
    delta = (expiry - today).days
    return TEMPLATE_OFFSETS.get(delta)


@dataclass
class Tenant:
    id: str
    subscription_expires_at: date
    status: str = "ACTIVE"
    auto_renew: bool = False
    email_opt_in: bool = True
    wa_opt_in: bool = False
    owner_phone: str | None = None
    updated_at: datetime | None = None
    plan: str = ""


def channels_for_tenant(t: Tenant) -> List[str]:
    channels: List[str] = []
    if t.email_opt_in:
        channels.append("email")
    if t.wa_opt_in and t.owner_phone:
        channels.append("whatsapp")
    return channels


def build_renew_url(plan: str, return_to: str, template_key: str) -> str:
    rt = quote(return_to, safe="")
    return (
        f"/admin/billing?plan={plan}&return_to={rt}"
        f"&utm_source=dunning&utm_campaign={template_key}"
    )


def should_show_banner(status: str, snoozed_until: date | None, today: date | None = None) -> bool:
    today = today or date.today()
    if snoozed_until and snoozed_until >= today:
        return False
    return status in {"GRACE", "EXPIRED"}


def _load_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def schedule_dunning(
    tenants: Iterable[Tenant],
    today: date | None = None,
    log_path: str | os.PathLike[str] = "dunning_events.log",
    max_per_day: int = 2,
) -> list[dict]:
    """Compute dunning events and append to log.

    Returns list of events created for this run.
    """
    today = today or date.today()
    log_file = Path(log_path)
    existing = _load_log(log_file)
    dedupe_keys = {e["dedupe_key"] for e in existing}
    per_tenant = {}
    for e in existing:
        key = (e["tenant_id"], e["when"].split("T")[0])
        per_tenant[key] = per_tenant.get(key, 0) + 1

    events: list[dict] = []
    now = datetime.utcnow().isoformat()
    for t in tenants:
        if t.status == "CANCELLED" or (t.status == "ACTIVE" and t.auto_renew):
            continue
        if t.status == "ACTIVE" and t.updated_at and datetime.utcnow() - t.updated_at < timedelta(hours=2):
            continue
        key = compute_template_key(t.subscription_expires_at, today)
        if not key:
            continue
        dedupe = f"{t.id}:{key}:{today.isoformat()}"
        if dedupe in dedupe_keys:
            continue
        count = per_tenant.get((t.id, today.isoformat()), 0)
        if count >= max_per_day:
            continue
        channels = channels_for_tenant(t)
        payload = {
            "tenant_id": t.id,
            "when": now,
            "template_key": key,
            "channels_sent": channels,
            "dedupe_key": dedupe,
        }
        payload["sha"] = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        events.append(payload)
        dedupe_keys.add(dedupe)
        per_tenant[(t.id, today.isoformat())] = count + 1

    if events:
        with log_file.open("a") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
    return events


__all__ = [
    "compute_template_key",
    "schedule_dunning",
    "Tenant",
    "channels_for_tenant",
    "build_renew_url",
    "should_show_banner",
]
