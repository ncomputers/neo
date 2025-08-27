#!/usr/bin/env python3
"""Synthetic monitor simulating a full guest order life-cycle.

Env variables:
- SYN_TENANT_ID
- SYN_TABLE_CODE
- SYN_MENU_ITEM_IDS (comma separated)
- SYN_UPI_VPA (optional)
- API_BASE_URL
- AUTH_TOKEN
- PUSHGATEWAY (optional)
- DRY_RUN (optional, bypass HTTP calls for tests)
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:  # optional prometheus pushgateway
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    CollectorRegistry = Gauge = push_to_gateway = None  # type: ignore

ARTIFACT_DIR = Path("synthetics")


def _http(method: str, url: str, headers: dict[str, str], payload: Any | None = None) -> tuple[int, Any]:
    if os.environ.get("DRY_RUN"):
        # minimal stubbed responses used in tests
        if url.endswith("/refund"):
            count = _http.refund_calls.get(headers["Idempotency-Key"], 0)
            _http.refund_calls[headers["Idempotency-Key"]] = count + 1
            status = 200
            body = {"status": "REFUNDED" if count == 0 else "NOOP"}
        elif url.endswith("/invoice.pdf"):
            status = 200
            body = b"Outlet Name\nTotal \xe2\x82\xb9" + b"0"*6000
        else:
            status = 200
            body = {"ok": True, "order_id": "o-1", "invoice_id": 1}
        return status, body

    data = json.dumps(payload).encode() if payload is not None else None
    req_headers = {"Content-Type": "application/json", **headers} if data else headers
    req = Request(url, data=data, headers=req_headers, method=method)
    with urlopen(req, timeout=10) as resp:  # noqa: S310
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        parsed = json.loads(body) if "application/json" in ctype else body
        return resp.status, parsed


_http.refund_calls = {}  # type: ignore[attr-defined]


def _push_metric(metrics: dict[str, Any]) -> None:
    if not push_to_gateway:
        return
    gateway = os.environ.get("PUSHGATEWAY")
    if not gateway:
        return
    registry = CollectorRegistry()
    g = Gauge("synthetic_order_success", "1 if synthetic order succeeded", registry=registry)
    g.set(1 if metrics["success"] else 0)
    try:
        push_to_gateway(gateway, job="synthetic_order_monitor", registry=registry)
    except Exception:  # pragma: no cover - best effort
        pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    required = [
        "SYN_TENANT_ID",
        "SYN_TABLE_CODE",
        "SYN_MENU_ITEM_IDS",
        "API_BASE_URL",
        "AUTH_TOKEN",
    ]
    for key in required:
        if key not in os.environ:
            raise RuntimeError(f"missing env {key}")

    tenant = os.environ["SYN_TENANT_ID"]
    table = os.environ["SYN_TABLE_CODE"]
    item_ids = [i.strip() for i in os.environ["SYN_MENU_ITEM_IDS"].split(",") if i.strip()]
    base = os.environ["API_BASE_URL"].rstrip("/")
    token = os.environ["AUTH_TOKEN"]
    vpa = os.environ.get("SYN_UPI_VPA")

    metrics: dict[str, Any] = {
        "success": False,
        "step_failed": None,
        "total_ms": 0,
        "kds_appear_ms": 0,
        "invoice_ms": 0,
        "refund_ms": 0,
        "http_status_map": {},
    }

    headers = {"Authorization": f"Bearer {token}"}
    idem = str(uuid.uuid4())
    start = time.perf_counter()
    try:
        # a) start guest session
        url = f"{base}/g/{tenant}/{table}/session"
        status, _ = _http("POST", url, headers)
        metrics["http_status_map"]["session"] = status

        # b) add items
        url = f"{base}/g/{tenant}/{table}/cart"
        payload = {"items": [{"item_id": iid, "qty": 1} for iid in item_ids[:2]]}
        status, _ = _http("POST", url, headers, payload)
        metrics["http_status_map"]["add_items"] = status

        # c) place order
        url = f"{base}/g/{tenant}/{table}/order"
        status, resp = _http("POST", url, headers, {})
        metrics["http_status_map"]["place_order"] = status
        order_id = resp.get("order_id", "1")

        # d) poll kds
        t0 = time.perf_counter()
        url = f"{base}/kds/{tenant}/tickets/{order_id}"
        status, _ = _http("GET", url, headers)
        metrics["http_status_map"]["kds"] = status
        metrics["kds_appear_ms"] = int((time.perf_counter() - t0) * 1000)

        # if KDS requires accept
        url = f"{base}/staff/kds/{order_id}/accept"
        status, _ = _http("POST", url, headers)
        metrics["http_status_map"]["kds_accept"] = status

        # e) generate invoice and download pdf
        t0 = time.perf_counter()
        url = f"{base}/g/{tenant}/{table}/bill"
        status, resp = _http("POST", url, headers, {})
        metrics["http_status_map"]["bill"] = status
        invoice_id = resp.get("invoice_id", 1)
        url = f"{base}/invoice/{invoice_id}/invoice.pdf"
        status, pdf = _http("GET", url, headers)
        metrics["http_status_map"]["invoice_pdf"] = status
        if isinstance(pdf, bytes):
            if len(pdf) <= 5 * 1024 or b"\xe2\x82\xb9" not in pdf:
                raise RuntimeError("invoice pdf invalid")
        metrics["invoice_ms"] = int((time.perf_counter() - t0) * 1000)

        # f) refund twice
        t0 = time.perf_counter()
        url = f"{base}/api/outlet/{tenant}/order/{order_id}/refund"
        rheaders = {**headers, "Idempotency-Key": idem}
        status, body = _http("POST", url, rheaders, {"vpa": vpa} if vpa else {})
        metrics["http_status_map"]["refund_1"] = status
        status2, body2 = _http("POST", url, rheaders, {"vpa": vpa} if vpa else {})
        metrics["http_status_map"]["refund_2"] = status2
        metrics["refund_ms"] = int((time.perf_counter() - t0) * 1000)
        if body2.get("status") not in {"REFUNDED", "NOOP"}:
            raise RuntimeError("refund not idempotent")

        metrics["success"] = True
    except Exception as exc:
        metrics["step_failed"] = metrics["step_failed"] or str(exc)
        # save artifacts
        ts = time.strftime("%Y%m%d-%H%M%S")
        outdir = ARTIFACT_DIR / ts
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "error.txt").write_text(str(exc))
        logging.error("synthetic monitor failed step=%s error=%s", metrics["step_failed"], exc)
        raise
    finally:
        metrics["total_ms"] = int((time.perf_counter() - start) * 1000)
        print(json.dumps(metrics))
        _push_metric(metrics)


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, RuntimeError) as exc:  # pragma: no cover - CLI
        logging.error("synthetic monitor error=%s", exc)
        raise
