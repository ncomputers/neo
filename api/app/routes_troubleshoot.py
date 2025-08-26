from __future__ import annotations

import os
import socket
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request

from .services import printer_watchdog

router = APIRouter()


@router.get("/admin/troubleshoot")
async def troubleshoot(request: Request) -> dict:
    """Run connectivity and version checks for admins."""
    tenant = request.headers.get("X-Tenant-ID", "")
    redis = request.app.state.redis

    # Printer heartbeat
    try:
        stale, _ = await printer_watchdog.check(redis, tenant)
        printer_ok = not stale
    except Exception:  # pragma: no cover - best effort
        printer_ok = False
    printer_next = "" if printer_ok else "Check printer power and network."

    # Time skew
    client_epoch = request.query_params.get("client_epoch")
    time_ok = False
    skew = None
    if client_epoch:
        try:
            client_epoch = int(client_epoch) / 1000
            server_epoch = datetime.now(timezone.utc).timestamp()
            skew = abs(server_epoch - client_epoch)
            time_ok = skew <= 120
        except ValueError:
            time_ok = False
    time_next = "" if time_ok else "Sync device clock."

    # DNS and latency
    dns_ok = False
    latency_ms = None
    try:
        start = time.monotonic()
        socket.gethostbyname("example.com")
        async with httpx.AsyncClient(timeout=2) as client:
            await client.get("https://example.com")
        latency_ms = int((time.monotonic() - start) * 1000)
        dns_ok = True
    except Exception:  # pragma: no cover - best effort
        dns_ok = False
    dns_next = "" if dns_ok else "Check network DNS and latency."

    # Software version mismatch
    server_version = os.getenv("APP_VERSION", "dev")
    client_version = request.headers.get("X-App-Version", "")
    version_ok = not client_version or client_version == server_version
    version_next = "" if version_ok else "Update app to latest version."

    return {
        "printer": {"ok": printer_ok, "next": printer_next},
        "time": {"ok": time_ok, "skew_s": skew, "next": time_next},
        "dns": {"ok": dns_ok, "latency_ms": latency_ms, "next": dns_next},
        "version": {
            "ok": version_ok,
            "server": server_version,
            "client": client_version,
            "next": version_next,
        },
    }
