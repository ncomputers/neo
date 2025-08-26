#!/usr/bin/env python3
"""Fetch sample invoice and KOT PDFs to catch template issues."""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

TIME_LIMIT = 2.0


def _fetch(url: str, out_path: Path) -> None:
    start = time.perf_counter()
    with urlopen(url, timeout=10) as resp:  # noqa: S310 # nosec - controlled URL
        data = resp.read()
        elapsed = time.perf_counter() - start
        if resp.status != 200:
            raise RuntimeError(f"{url} -> {resp.status}")
        if elapsed > TIME_LIMIT:
            raise RuntimeError(f"{url} took {elapsed:.2f}s")
    out_path.write_bytes(data)
    logging.info("ok %s %.2fs %d bytes", url, elapsed, len(data))


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF render smoke test")
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="API base URL"
    )
    parser.add_argument("--tenant", default="demo", help="Tenant identifier")
    parser.add_argument("--outdir", default=".", help="Directory to store PDFs")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    endpoints = [
        (f"{args.base_url}/invoice/123/pdf?size=A4", outdir / "invoice.pdf"),
        (
            f"{args.base_url}/api/outlet/{args.tenant}/kot/sample.pdf",
            outdir / "kot.pdf",
        ),
    ]

    for url, path in endpoints:
        _fetch(url, path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        main()
    except (HTTPError, URLError, RuntimeError) as exc:
        logging.error("pdf smoke failed error=%s", exc)
        raise
