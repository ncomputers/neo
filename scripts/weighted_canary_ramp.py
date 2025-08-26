#!/usr/bin/env python3
"""Safer weighted ramp with automatic rollback on failed health checks.

Renders the Nginx upstream from a template and gradually shifts traffic from the
old stack to the new one at 5%, 25%, 50% and finally 100% weights. After each
step the script performs a readiness probe and verifies that the error budget is
not being burned. If any check fails the configuration is reverted to route
100% to the old stack.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path
from string import Template
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import json
from urllib.request import Request


def run(cmd: list[str]) -> None:
    """Run *cmd* and raise if it exits non-zero."""
    subprocess.check_call(cmd)


def healthcheck(url: str, timeout: int = 60) -> None:
    """Poll *url* until it returns HTTP 200 or *timeout* seconds elapse."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=5) as resp:  # noqa: S310 # nosec - controlled URL
                if resp.status == 200:
                    return
        except (HTTPError, URLError):
            pass
        time.sleep(1)
    raise RuntimeError(f"healthcheck failed for {url}")


def render_conf(template: Path, dest: Path, new: str, old: str, weight: int) -> None:
    """Render *template* with weights to *dest* and reload Nginx."""
    tpl = Template(template.read_text())
    dest.write_text(
        tpl.substitute(new=new, old=old, new_weight=weight, old_weight=100 - weight)
    )
    run(["sudo", "nginx", "-t"])
    run(["sudo", "systemctl", "reload", "nginx"])


def check_error_budget(url: str, min_budget: float) -> None:
    """Abort if any route has less than *min_budget* remaining."""
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=5) as resp:  # noqa: S310 # nosec - controlled URL
        data = json.load(resp)
    for route, stats in data.items():
        budget = float(stats.get("error_budget", 1.0))
        if budget < min_budget:
            raise RuntimeError(f"error budget burned for {route}: {budget:.2%}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Weighted ramp with health checks and rollback"
    )
    parser.add_argument("--new", required=True, help="hostname of new upstream")
    parser.add_argument("--old", required=True, help="hostname of old upstream")
    parser.add_argument(
        "--template",
        default="/etc/nginx/sites-available/neo.conf.tmpl",
        help="path to Nginx config template",
    )
    parser.add_argument(
        "--nginx-conf",
        default="/etc/nginx/sites-available/neo.conf",
        help="path to rendered Nginx config",
    )
    parser.add_argument(
        "--base-url",
        default="https://example.com",
        help="base URL for health checks",
    )
    parser.add_argument(
        "--min-budget",
        type=float,
        default=0.99,
        help="minimum acceptable remaining error budget",
    )
    args = parser.parse_args()

    template = Path(args.template)
    conf = Path(args.nginx_conf)

    try:
        for pct in (5, 25, 50, 100):
            render_conf(template, conf, args.new, args.old, pct)
            healthcheck(f"{args.base_url}/ready")
            check_error_budget(f"{args.base_url}/admin/ops/slo", args.min_budget)
    except Exception:
        render_conf(template, conf, args.new, args.old, 0)
        raise


if __name__ == "__main__":
    main()
