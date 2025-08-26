#!/usr/bin/env python3
"""Fetch PWA icons for install prompts without bundling binaries."""

from __future__ import annotations

import urllib.request
from pathlib import Path

ICON_SOURCES = {
    "neo-qr-192.png": "https://placehold.co/192x192.png?text=Neo%20QR",
    "neo-qr-512.png": "https://placehold.co/512x512.png?text=Neo%20QR",
}

ICON_DIR = Path(__file__).resolve().parents[1] / "static" / "icons"


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in ICON_SOURCES.items():
        dest = ICON_DIR / name
        urllib.request.urlretrieve(url, dest)  # nosec B310


if __name__ == "__main__":
    main()
