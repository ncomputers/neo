#!/usr/bin/env python3
"""Wrapper to generate a QR poster pack for the pilot tenant."""

from __future__ import annotations

import argparse

from qr_poster_pack import generate_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Render QR pack for a tenant")
    parser.add_argument("--tenant", default="pilot", help="Tenant identifier")
    parser.add_argument("--size", choices=["A4", "A5"], default="A4")
    parser.add_argument(
        "--output", default="pilot_qr_pack.zip", help="Output ZIP filename"
    )
    args = parser.parse_args()

    data = generate_pack(args.tenant, args.size)
    with open(args.output, "wb") as fh:
        fh.write(data)


if __name__ == "__main__":
    main()
