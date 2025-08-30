#!/usr/bin/env python3
"""Nightly export of BI-friendly tables to Parquet or CSV.

This script auto-configures ``PYTHONPATH`` to include the repository root so
imports work when executed directly.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone

import boto3
from sqlalchemy import create_engine, text

try:  # optional dependency
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover - runtime optional
    pa = None  # type: ignore[assignment]

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app.bi_dump import build_manifest


def _required_env(name: str) -> str:
    """Return required environment variable or raise a helpful error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def _daterange(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _dump_dataset(engine, query: str, params: dict, out_path: Path) -> str:
    with engine.begin() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]

    if pa is not None:
        table = pa.Table.from_pylist(rows)
        pq.write_table(table, out_path)
        return "parquet"
    else:
        fieldnames = rows[0].keys() if rows else []
        with gzip.open(out_path, "wt", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return "csv.gz"


def _upload(client: boto3.client, bucket: str, path: Path, key: str) -> str:
    client.upload_file(str(path), bucket, key)
    return key


def main(day: date) -> dict:
    dsn = _required_env("DWH_DB_DSN")
    engine = create_engine(dsn)

    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("DWH_S3_URL"),
        aws_access_key_id=os.getenv("DWH_S3_KEY"),
        aws_secret_access_key=os.getenv("DWH_S3_SECRET"),
    )
    bucket = _required_env("DWH_S3_BUCKET")
    prefix = os.getenv("DWH_PREFIX", "").strip("/")
    if prefix:
        prefix = f"{prefix}/"

    start, end = _daterange(day)
    tmp_dir = Path(os.getenv("DWH_TMP_DIR", "/tmp")) / day.isoformat()  # nosec B108
    tmp_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "orders": "SELECT * FROM orders WHERE placed_at >= :start AND placed_at < :end",
        "order_items": "SELECT i.* FROM order_items i JOIN orders o ON o.id = i.order_id WHERE o.placed_at >= :start AND o.placed_at < :end",
        "payments": "SELECT * FROM payments WHERE created_at >= :start AND created_at < :end",
    }

    files = []
    for name, query in datasets.items():
        suffix = "parquet" if pa is not None else "csv.gz"
        out_path = tmp_dir / f"{name}.{suffix}"
        _dump_dataset(engine, query, {"start": start, "end": end}, out_path)
        key = f"{prefix}{name}/dt={day.isoformat()}/{name}.{suffix}"
        _upload(s3, bucket, out_path, key)
        files.append({"dataset": name, "s3_key": key})

    manifest = build_manifest(day, files)
    manifest_key = f"{prefix}manifest/{day.isoformat()}.json"
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest).encode("utf-8"),
        ContentType="application/json",
    )
    return manifest


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Nightly DWH dump")
    parser.add_argument(
        "--day",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=1),
        help="Day to export (defaults to yesterday)",
    )
    args = parser.parse_args()
    main(args.day)


if __name__ == "__main__":  # pragma: no cover - script entry
    _cli()
