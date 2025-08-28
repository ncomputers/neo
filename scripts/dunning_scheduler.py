from __future__ import annotations

"""Daily scheduler for subscription dunning notifications."""

from datetime import date
from pathlib import Path
import os

from api.app.dunning import Tenant, schedule_dunning
from api.app.main import TENANTS


def _load_tenants() -> list[Tenant]:
    tenants: list[Tenant] = []
    for tid, info in TENANTS.items():
        expiry = info.get("subscription_expires_at")
        if not expiry:
            continue
        if hasattr(expiry, "date"):
            expiry = expiry.date()
        tenants.append(
            Tenant(
                id=tid,
                subscription_expires_at=expiry,
                status=info.get("status", "ACTIVE"),
                auto_renew=info.get("auto_renew", False),
                email_opt_in=info.get("dunning_email_opt_in", True),
                wa_opt_in=info.get("dunning_wa_opt_in", False),
                owner_phone=info.get("owner_phone"),
                updated_at=info.get("updated_at"),
                plan=info.get("plan", ""),
            )
        )
    return tenants


def main() -> None:
    tenants = _load_tenants()
    max_per_day = int(os.getenv("DUNNING_MAX_PER_DAY_PER_TENANT", "2"))
    schedule_dunning(
        tenants,
        today=date.today(),
        log_path=Path("dunning_events.log"),
        max_per_day=max_per_day,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
