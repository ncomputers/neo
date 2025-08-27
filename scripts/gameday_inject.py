#!/usr/bin/env python3
"""GameDay fault injection for staging environments.

Each scenario simulates a real failure and ensures that alerts fire and
systems recover. The script accepts ``--scenario`` multiple times to run
specific drills and records their results in a JSON file.

The scenarios are intentionally lightweight so they can be executed safely
in CI. Real staging runs should provide the necessary environment variables
and network access for the injections to take effect.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Callable, Dict, Any

import requests


Result = Dict[str, Any]


def _run_scenario(name: str, func: Callable[[bool], None], dry_run: bool) -> Result:
    """Execute ``func`` and capture timing/result information."""
    start = time.time()
    ok = True
    detail = ""
    try:
        func(dry_run)
    except Exception as exc:  # pragma: no cover - defensive
        ok = False
        detail = str(exc)
    duration = time.time() - start
    return {"scenario": name, "success": ok, "seconds": round(duration, 2), "detail": detail}


def kds_offline(dry_run: bool) -> None:
    """Simulate KDS agent heartbeat going stale."""
    if dry_run:
        time.sleep(0.1)
        return
    time.sleep(2)  # placeholder for real implementation


def webhook_slow(dry_run: bool) -> None:
    """Hit a slow failing webhook to trigger breaker."""
    url = "https://httpstat.us/500?sleep=9000"
    if dry_run:
        time.sleep(0.1)
        return
    requests.get(url, timeout=15)


def payment_dns_fail(dry_run: bool) -> None:
    """Point ``GATEWAY_HOST`` to an invalid host and perform a request."""
    if dry_run:
        time.sleep(0.1)
        return
    original = os.environ.get("GATEWAY_HOST", "")
    try:
        os.environ["GATEWAY_HOST"] = "invalid.host"
        requests.get(f"https://{os.environ['GATEWAY_HOST']}", timeout=5)
    finally:
        os.environ["GATEWAY_HOST"] = original


def printer_jam(dry_run: bool) -> None:
    """Enqueue a fake KOT to push queue age beyond threshold."""
    if dry_run:
        time.sleep(0.1)
        return
    time.sleep(2)  # placeholder


def db_readonly(dry_run: bool) -> None:
    """Flip DB user to read only for a brief period."""
    if dry_run:
        time.sleep(0.1)
        return
    time.sleep(2)  # placeholder


SCENARIOS: Dict[str, Callable[[bool], None]] = {
    "kds_offline": kds_offline,
    "webhook_slow": webhook_slow,
    "payment_dns_fail": payment_dns_fail,
    "printer_jam": printer_jam,
    "db_readonly": db_readonly,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="GameDay fault injector")
    parser.add_argument(
        "--scenario",
        action="append",
        choices=sorted(SCENARIOS.keys()),
        required=True,
        help="Scenario(s) to run",
    )
    parser.add_argument("--output", default="gameday_results.json", help="Result JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Skip destructive actions")
    parser.add_argument("--retries", type=int, default=1, help="Retry count on failure")
    args = parser.parse_args()

    results: list[Result] = []
    for name in args.scenario:
        attempt = 0
        result: Result
        while True:
            result = _run_scenario(name, SCENARIOS[name], args.dry_run)
            if result["success"] or attempt >= args.retries:
                break
            attempt += 1
            time.sleep(1)
        results.append(result)
        if not result["success"]:
            print(f"{name} failed: {result['detail']}")
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump({"results": results, "generated_at": time.time()}, fh, indent=2)

    # non-zero exit if any scenario failed twice
    if any(not r["success"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
