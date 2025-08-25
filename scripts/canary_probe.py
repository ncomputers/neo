#!/usr/bin/env python3
"""Synthetic canary probe performing an order round-trip.

The probe places a tiny order via guest endpoints, immediately cancels it via
admin APIs and emits a log line (and optional Prometheus metric). It is intended
for external uptime monitoring.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:  # optional Prometheus pushgateway support
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway  # type: ignore
except Exception:  # pragma: no cover - dependency optional
    CollectorRegistry = Gauge = push_to_gateway = None  # type: ignore


def _request(method: str, url: str, headers: dict[str, str], payload: dict[str, Any]) -> Any:
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method=method)
    with urlopen(req, timeout=10) as resp:  # noqa: S310 - controlled URL
        body = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"{method} {url} -> {resp.status} {body.decode()}")
        return json.loads(body)


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
            "PATCH",
            f"{args.base_url}/tables/{args.table}/order/0",
            {"X-Tenant-ID": args.tenant},
            {"quantity": 0, "admin": True},
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
