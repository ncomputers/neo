#!/usr/bin/env python3
"""Compare `.env.example` with required environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Set

from api.app.config.validate import REQUIRED_ENVS


def _read_example(path: Path) -> Set[str]:
    return {
        line.split("=", 1)[0].strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def main() -> None:
    example_path = Path(".env.example")
    if not example_path.exists():
        print(".env.example not found")
        return

    example_vars = _read_example(example_path)
    required = set(REQUIRED_ENVS)

    missing = required - example_vars
    extra = example_vars - required

    if missing:
        print("Missing in .env.example:", ", ".join(sorted(missing)))
    if extra:
        print("Extra in .env.example:", ", ".join(sorted(extra)))
    if not missing and not extra:
        print(".env.example matches REQUIRED_ENVS")


if __name__ == "__main__":
    main()
