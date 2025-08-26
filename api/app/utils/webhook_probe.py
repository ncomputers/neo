"""Utilities to probe webhook destinations for SLA compliance."""

from __future__ import annotations

import math
import ssl
import time
from datetime import datetime, timezone

import httpx

from ..security.webhook_egress import is_allowed_url

SLA_MS = 1000


async def probe_webhook(url: str) -> dict:
    """Probe ``url`` and return latency, TLS and status information."""
    allowed = is_allowed_url(url)
    warnings: list[str] = []
    latencies: list[int] = []
    codes: list[int | None] = []
    tls_version: str | None = None
    tls_expires_at: str | None = None
    tls_self_signed = False

    async with httpx.AsyncClient(timeout=5) as client:
        for _ in range(3):
            start = time.monotonic()
            try:
                resp = await client.head(url)
                codes.append(resp.status_code)
                stream = resp.extensions.get("network_stream")
                if stream:
                    ssl_obj = stream.get_extra_info("ssl_object")
                    if ssl_obj:
                        tls_version = ssl_obj.version()
                        cert = ssl_obj.getpeercert()
                        if cert and "notAfter" in cert:
                            ts = ssl.cert_time_to_seconds(cert["notAfter"])
                            tls_expires_at = (
                                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                            )
            except httpx.HTTPError as exc:
                codes.append(None)
                cause = getattr(exc, "__cause__", None)
                if isinstance(cause, ssl.SSLCertVerificationError):
                    tls_self_signed = True
            finally:
                latencies.append(int((time.monotonic() - start) * 1000))

    if not allowed:
        warnings.append("ip_not_allowed")
    if tls_self_signed:
        warnings.append("tls_self_signed")

    lat_sorted = sorted(latencies)
    p50 = lat_sorted[len(lat_sorted) // 2]
    p95_index = max(math.ceil(len(lat_sorted) * 0.95) - 1, 0)
    p95 = lat_sorted[p95_index]
    if p95 > SLA_MS:
        warnings.append("slow")
    if any(code is None or code >= 400 for code in codes):
        warnings.append("bad_status")

    return {
        "tls": {"version": tls_version, "expires_at": tls_expires_at},
        "latency_ms": {"p50": p50, "p95": p95},
        "status_codes": codes,
        "allowed": allowed,
        "warnings": warnings,
    }
