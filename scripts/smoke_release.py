#!/usr/bin/env python3
"""Release smoke test placing and voiding an order."""

from __future__ import annotations

import argparse
import json
import logging
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request(
    method: str, url: str, headers: dict[str, str], payload: dict[str, Any]
) -> Any:
    data = json.dumps(payload).encode()
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method=method,
    )
    with urlopen(req, timeout=10) as resp:  # noqa: S310 # nosec - controlled URL
        body = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"{method} {url} -> {resp.status} {body.decode()}")
        return json.loads(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Release smoke test")
    parser.add_argument("--tenant", required=True, help="Tenant identifier")
    parser.add_argument("--table", required=True, help="Table token")
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="Base URL for API endpoints"
    )
    args = parser.parse_args()

    idem = f"smoke-{uuid.uuid4()}"
    headers = {"X-Tenant-ID": args.tenant, "Idempotency-Key": idem}

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    order = _request(
        "POST",
        f"{args.base_url}/g/{args.table}/order",
        headers,
        {"items": [{"item_id": "smoke", "qty": 1}]},
    )
    order_id = order["data"]["order_id"]
    _request(
        "PATCH",
        f"{args.base_url}/tables/{args.table}/order/0",
        {"X-Tenant-ID": args.tenant},
        {"quantity": 0, "admin": True},
    )
    logging.info(
        "smoke test ok tenant=%s table=%s order=%s", args.tenant, args.table, order_id
    )


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, RuntimeError, KeyError) as exc:
        logging.error("smoke test failed error=%s", exc)
        raise
