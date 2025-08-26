#!/usr/bin/env python3
"""Nightly parquet dumps for BI."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import create_engine, text

from api.app.bi_dump import build_manifest


def _daterange(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def _dump_dataset(engine, query: str, params: dict, out_path: Path) -> None:
    with engine.begin() as conn:
        result = conn.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, out_path)


def _upload(client: boto3.client, bucket: str, path: Path, key: str) -> str:
    client.upload_file(str(path), bucket, key)
    return key


def main(day: date) -> dict:
    dsn = os.environ["BI_DB_DSN"]
    engine = create_engine(dsn)

    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("BI_S3_ENDPOINT"),
        region_name=os.getenv("BI_S3_REGION"),
        aws_access_key_id=os.getenv("BI_S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("BI_S3_SECRET_KEY"),
    )
    bucket = os.environ["BI_S3_BUCKET"]

    start, end = _daterange(day)
    tmp_dir = Path(os.getenv("BI_TMP_DIR", "/tmp")) / day.isoformat()
    tmp_dir.mkdir(parents=True, exist_ok=True)

    datasets = {
        "orders": "SELECT * FROM orders WHERE placed_at >= :start AND placed_at < :end",
        "items": "SELECT i.* FROM order_items i JOIN orders o ON o.id = i.order_id WHERE o.placed_at >= :start AND o.placed_at < :end",
        "payments": "SELECT * FROM payments WHERE created_at >= :start AND created_at < :end",
    }

    files = []
    for name, query in datasets.items():
        out_path = tmp_dir / f"{name}.parquet"
        _dump_dataset(engine, query, {"start": start, "end": end}, out_path)
        key = f"{name}/d={day.isoformat()}/{name}.parquet"
        _upload(s3, bucket, out_path, key)
        files.append({"dataset": name, "s3_key": key})

    manifest = build_manifest(day, files)
    manifest_key = f"manifest/{day.isoformat()}.json"
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=json.dumps(manifest).encode("utf-8"),
        ContentType="application/json",
    )
    return manifest


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Nightly BI parquet dump")
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
