#!/usr/bin/env python3
"""Blue/green deployment helper.

Creates a new application instance, gates on preflight/ready health, runs
smoke and canary checks, flips the Nginx upstream and finally retires the
previous instance. Smoke failures trigger an automatic rollback.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SCRIPT_DIR = Path(__file__).resolve().parent


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Blue/green deployment helper")
    parser.add_argument("--new", required=True, help="systemd unit for new version")
    parser.add_argument("--old", required=True, help="systemd unit for old version")
    parser.add_argument(
        "--nginx-conf",
        default="/etc/nginx/sites-available/neo.conf",
        help="path to Nginx config",
    )
    parser.add_argument("--tenant", required=True, help="tenant for smoke/canary")
    parser.add_argument("--table", required=True, help="table token for smoke/canary")
    parser.add_argument(
        "--base-url",
        default="https://example.com",
        help="base URL for health checks and probes",
    )
    args = parser.parse_args()

    run(["systemctl", "start", args.new])
    healthcheck(f"{args.base_url}/preflight")
    healthcheck(f"{args.base_url}/ready")

    try:
        run(
            [
                sys.executable,
                str(SCRIPT_DIR / "canary_probe.py"),
                "--tenant",
                args.tenant,
                "--table",
                args.table,
                "--base-url",
                args.base_url,
                "--minimal",
            ]
        )
    except subprocess.CalledProcessError:
        run(["systemctl", "stop", args.new])
        raise
    run(
        [
            sys.executable,
            str(SCRIPT_DIR / "canary_probe.py"),
            "--tenant",
            args.tenant,
            "--table",
            args.table,
            "--base-url",
            args.base_url,
        ]
    )

    run(
        [
            "sudo",
            "sed",
            "-e",
            f"s/upstream {args.old}/upstream {args.new}/",
            "-i",
            args.nginx_conf,
        ]
    )
    run(["sudo", "nginx", "-t"])
    run(["sudo", "systemctl", "reload", "nginx"])

    run(["systemctl", "stop", args.old])


if __name__ == "__main__":
    main()
