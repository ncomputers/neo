from datetime import date

from api.app.bi_dump import build_manifest


def test_build_manifest_structure() -> None:
    day = date(2023, 1, 1)
    files = [
        {"dataset": "orders", "s3_key": "orders/d=2023-01-01/orders.parquet"},
        {"dataset": "items", "s3_key": "items/d=2023-01-01/items.parquet"},
    ]
    manifest = build_manifest(day, files)
    assert manifest["date"] == "2023-01-01"
    assert manifest["files"] == files
