"""Minimal analytics helpers with tenant consent and PII redaction."""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict

import httpx

from .. import flags


def _consented_tenants() -> set[str]:
    """Return tenants that have opted into analytics."""

    raw = os.getenv("ANALYTICS_TENANTS", "")
    return {t.strip() for t in raw.split(",") if t.strip()}


def _redact(properties: Dict[str, Any]) -> Dict[str, Any]:
    """Drop common PII fields from ``properties``."""

    pii_keys = {"email", "phone", "name"}
    return {k: v for k, v in properties.items() if k.lower() not in pii_keys}


async def track(tenant: str, event: str, properties: Dict[str, Any] | None = None) -> None:
    """Send ``event`` with ``properties`` for ``tenant`` if enabled and consented."""

    if not flags.get("analytics"):
        return
    if tenant not in _consented_tenants():
        return

    props = _redact(properties or {})
    ph_key = os.getenv("POSTHOG_API_KEY")
    mp_token = os.getenv("MIXPANEL_TOKEN")
    if ph_key:
        await _posthog(ph_key, tenant, event, props)
    elif mp_token:
        await _mixpanel(mp_token, tenant, event, props)


async def _posthog(api_key: str, tenant: str, event: str, props: Dict[str, Any]) -> None:
    host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
    payload = {
        "api_key": api_key,
        "distinct_id": tenant,
        "event": event,
        "properties": props,
    }
    async with httpx.AsyncClient(timeout=2) as client:
        await client.post(f"{host}/capture/", json=payload)


async def _mixpanel(token: str, tenant: str, event: str, props: Dict[str, Any]) -> None:
    payload = {
        "event": event,
        "properties": {"token": token, "distinct_id": tenant, **props},
    }
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    async with httpx.AsyncClient(timeout=2) as client:
        await client.post("https://api.mixpanel.com/track", data={"data": data})


__all__ = ["track"]

