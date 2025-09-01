"""PostHog/Mixpanel analytics with tenant consent and batching."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

PII_KEYS = {"email", "phone", "name"}

_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
_worker_started = False

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    """Return True if analytics globally enabled."""
    val = os.getenv("TENANT_ANALYTICS_ENABLED", "").lower()
    return val in {"1", "true", "yes", "on"}


def _consented_tenants() -> set[str]:
    """Return tenants that have opted into analytics."""
    raw = os.getenv("ANALYTICS_TENANTS", "")
    return {t.strip() for t in raw.split(",") if t.strip()}


def _redact(props: Dict[str, Any]) -> Dict[str, Any]:
    """Drop common PII fields from ``props``."""
    return {k: v for k, v in props.items() if k.lower() not in PII_KEYS}


def _ensure_worker() -> None:
    """Start background sender if not already running."""
    global _worker_started
    if _worker_started:
        return
    if os.getenv("DEBUG") or os.getenv("TESTING"):
        return
    loop = asyncio.get_event_loop()
    loop.create_task(_worker())
    _worker_started = True


async def track(
    tenant: str, event: str, properties: Dict[str, Any] | None = None
) -> None:
    """Queue ``event`` for ``tenant`` if enabled and consented."""
    if not _enabled():
        return
    if tenant not in _consented_tenants():
        return

    props = _redact(properties or {})
    await _queue.put({"distinct_id": tenant, "event": event, "properties": props})
    _ensure_worker()
    await _queue.join()


async def _worker() -> None:
    """Background task that flushes queued events."""
    while True:
        batch: List[Dict[str, Any]] = [await _queue.get()]
        while len(batch) < 20:
            try:
                batch.append(_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        try:
            await _send(batch)
        finally:
            for _ in batch:
                _queue.task_done()


async def _send(batch: List[Dict[str, Any]]) -> None:
    """Transmit ``batch`` to PostHog or Mixpanel with retries."""
    ph_key = os.getenv("POSTHOG_API_KEY")
    mp_token = os.getenv("MIXPANEL_TOKEN")
    if not ph_key and not mp_token:
        return

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                if ph_key:
                    host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
                    payload = {"api_key": ph_key, "batch": batch}
                    await client.post(f"{host}/batch/", json=payload)
                elif mp_token:
                    for evt in batch:
                        payload = {
                            "event": evt["event"],
                            "properties": {
                                "token": mp_token,
                                "distinct_id": evt["distinct_id"],
                                **evt["properties"],
                            },
                        }
                        data = base64.b64encode(json.dumps(payload).encode()).decode()
                        encoded_bytes = urlencode({"data": data}).encode()
                        await client.post(
                            "https://api.mixpanel.com/track",
                            content=encoded_bytes,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded"
                            },
                        )
            break
        except httpx.HTTPError as exc:  # network issue
            logger.warning("Analytics batch send failed: %s", exc)
            if attempt == 2:
                raise
            await asyncio.sleep(2**attempt)
        except Exception:
            logger.exception("Unexpected analytics error")
            raise


__all__ = ["track"]
