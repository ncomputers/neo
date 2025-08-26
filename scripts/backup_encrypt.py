#!/usr/bin/env python3
"""Encrypt a backup file using age."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def encrypt(path: Path, recipient: str) -> Path:
    """Encrypt ``path`` to ``path``.age using ``recipient``."""
    output = path.with_suffix(path.suffix + ".age")
    subprocess.run(
        [
            "age",
            "--encrypt",
            "-r",
            recipient,
            "-o",
            str(output),
            str(path),
        ],
        check=True,
    )
    path.unlink()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt backup file with age")
    parser.add_argument("path", type=Path, help="Path to dump file")
    parser.add_argument(
        "--recipient",
        "-r",
        help="age public key; falls back to BACKUP_PUBLIC_KEY env var",
    )
    args = parser.parse_args()
    recipient = args.recipient or os.environ.get("BACKUP_PUBLIC_KEY")
    if not recipient:
        parser.error("recipient required via --recipient or BACKUP_PUBLIC_KEY env")
    encrypt(args.path, recipient)


if __name__ == "__main__":  # pragma: no cover
    main()
