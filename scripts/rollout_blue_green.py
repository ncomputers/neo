#!/usr/bin/env python3
"""Roll forward helper for blue/green deployments.

Updates a deployment to a new image tag and waits for the rollout to finish.
"""

from __future__ import annotations

import argparse
import subprocess
from typing import Sequence


def _run(cmd: Sequence[str], dry_run: bool) -> None:
    """Run *cmd* unless ``dry_run`` is true."""
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Blue/green rollout helper")
    parser.add_argument(
        "--env", required=True, choices=["prod", "staging"], help="Target environment"
    )
    parser.add_argument("--to", required=True, help="Deployment tag to roll out")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )
    args = parser.parse_args()

    deployment = f"web-{args.env}"
    image = f"myapp:{args.to}"

    cmds = [
        ["kubectl", "set", "image", f"deploy/{deployment}", f"app={image}"],
        ["kubectl", "rollout", "status", f"deploy/{deployment}", "--timeout=300s"],
    ]
    for cmd in cmds:
        _run(cmd, args.dry_run)

    print(f"Rolled out {args.env} to {args.to}")


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
