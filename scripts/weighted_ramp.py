#!/usr/bin/env python3
"""Gradually shift traffic between blue/green stacks using Nginx weights."""

from __future__ import annotations

import argparse
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


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


def set_weights(conf: str, new: str, old: str, weight: int) -> None:
    """Adjust *new*/*old* weights in *conf* to *weight* and 100-weight."""
    run(
        [
            "sudo",
            "sed",
            "-E",
            "-e",
            f"s/server {new} weight=[0-9]+/server {new} weight={weight}/",
            "-e",
            f"s/server {old} weight=[0-9]+/server {old} weight={100 - weight}/",
            "-i",
            conf,
        ]
    )
    run(["sudo", "nginx", "-t"])
    run(["sudo", "systemctl", "reload", "nginx"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gradually ramp traffic to the new stack via Nginx weights"
    )
    parser.add_argument("--new", required=True, help="hostname of new upstream")
    parser.add_argument("--old", required=True, help="hostname of old upstream")
    parser.add_argument(
        "--nginx-conf",
        default="/etc/nginx/sites-available/neo.conf",
        help="path to Nginx config",
    )
    parser.add_argument(
        "--base-url",
        default="https://example.com",
        help="base URL for health checks",
    )
    args = parser.parse_args()

    for pct in (5, 25, 50):
        set_weights(args.nginx_conf, args.new, args.old, pct)
        healthcheck(f"{args.base_url}/ready")


if __name__ == "__main__":
    main()
