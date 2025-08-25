#!/usr/bin/env python3
"""Synthetic canary probe performing an end-to-end order round-trip.

The probe places a tiny order, generates a bill, exercises the checkout flow,
marks the order as paid and fetches an invoice PDF. It emits a log line (and
optional Prometheus metric) and is intended for external uptime monitoring.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jose import jwt

try:  # optional Prometheus pushgateway support
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    CollectorRegistry = Gauge = push_to_gateway = None  # type: ignore


def _request(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    req_headers = {"Content-Type": "application/json", **headers} if data else headers
    req = Request(url, data=data, headers=req_headers, method=method)
    with urlopen(req, timeout=10) as resp:  # noqa: S310 - controlled URL
        body = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"{method} {url} -> {resp.status} {body.decode(errors='ignore')}")
        ctype = resp.headers.get("Content-Type", "")
        return json.loads(body) if "application/json" in ctype else body


def _emit_metric(ok: bool) -> None:
    if not push_to_gateway:
        return
    gateway = os.environ.get("PUSHGATEWAY")
    if not gateway:
        return
    registry = CollectorRegistry()
    g = Gauge("canary_probe_ok", "1 if canary probe succeeded else 0", registry=registry)
    g.set(1 if ok else 0)
    try:
        push_to_gateway(gateway, job="neo_canary_probe", registry=registry)
    except Exception:  # pragma: no cover - best effort
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic canary order probe")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--table", required=True, help="Table token")
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="Base URL for API endpoints"
    )
    args = parser.parse_args()

    idem = f"canary-{uuid.uuid4()}"
    headers = {"X-Tenant-ID": args.tenant, "Idempotency-Key": idem}

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ok = False
    try:
        order = _request(
            "POST",
            f"{args.base_url}/g/{args.table}/order",
            headers,
            {"items": [{"item_id": "canary", "qty": 1}]},
        )
        order_id = order["data"]["order_id"]

        _request(
            "GET",
            f"{args.base_url}/api/outlet/{args.tenant}/kot/{order_id}.pdf",
            {},
        )

        _request(
            "POST",
            f"{args.base_url}/g/{args.table}/bill",
            headers,
            {},
        )

        _request(
            "POST",
            f"{args.base_url}/api/outlet/{args.tenant}/checkout/start",
            {},
            {"invoice_id": 1, "amount": 1},
        )

        _request(
            "POST",
            f"{args.base_url}/tables/{args.table}/pay",
            {},
        )

        _request(
            "GET",
            f"{args.base_url}/invoice/1/pdf",
            {},
        )

        secret = os.environ.get("JWT_SECRET", "supersecret")
        token = jwt.encode(
            {
                "sub": "canary",
                "role": "super_admin",
                "exp": datetime.utcnow() + timedelta(minutes=5),
            },
            secret,
            algorithm="HS256",
        )
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        _request(
            "POST",
            f"{args.base_url}/api/outlet/{args.tenant}/digest/run?date={yesterday}",
            {"Authorization": f"Bearer {token}"},
            {},
        )

        logging.info(
            "canary probe ok tenant=%s table=%s order=%s", args.tenant, args.table, order_id
        )
        ok = True
    except (HTTPError, URLError, RuntimeError, KeyError) as exc:
        logging.error(
            "canary probe failed tenant=%s table=%s error=%s", args.tenant, args.table, exc
        )
        raise
    finally:
        _emit_metric(ok)


if __name__ == "__main__":
    main()
