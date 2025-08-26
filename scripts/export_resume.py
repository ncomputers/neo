#!/usr/bin/env python3
"""Download export data handling cursor-based resume.

This CLI streams an export endpoint that supports cursor pagination and writes
all chunks to a file. The ``Next-Cursor`` response header is used to fetch
subsequent pages. If the process is interrupted, rerun the script with the
previously printed cursor using ``--cursor``.
"""

from __future__ import annotations

import argparse
import sys

import requests


def stream(url: str, output: str, cursor: str | None) -> None:
    params: dict[str, str] = {}
    cur: str | None = cursor
    with open(output, "ab") as fh:
        while True:
            if cur:
                params["cursor"] = cur
            with requests.get(url, params=params, stream=True) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
            cur = resp.headers.get("Next-Cursor") or resp.headers.get("X-Cursor")
            if not cur:
                break
            print(f"next cursor: {cur}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download export handling cursor resume"
    )
    parser.add_argument("--url", required=True, help="Export endpoint URL")
    parser.add_argument("--output", required=True, help="File path to write")
    parser.add_argument("--cursor", help="Cursor to resume from")
    args = parser.parse_args()
    stream(args.url, args.output, args.cursor)


if __name__ == "__main__":
    main()
