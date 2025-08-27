# DWH Parquet Dumps

The `scripts/dwh_parquet_dump.py` helper exports `orders`, `order_items` and
`payments` for a given day. Datasets are written as Parquet files when
`pyarrow` is available and fall back to gzipped CSV otherwise. Each dataset is
partitioned by date and uploaded to an S3-compatible bucket along with a daily
manifest.

## Configuration

Set the following environment variables:

- `DWH_DB_DSN` – Database DSN for the tenant data
- `DWH_S3_URL` – S3 endpoint URL
- `DWH_S3_KEY`, `DWH_S3_SECRET` – Bucket credentials
- `DWH_S3_BUCKET` – Destination bucket
- `DWH_PREFIX` – Optional key prefix within the bucket
- `DWH_TMP_DIR` – Optional temp directory (defaults to `/tmp`)

Each run uploads files under `<prefix><dataset>/dt=<YYYY-MM-DD>/` and writes a
manifest to `<prefix>manifest/<YYYY-MM-DD>.json` listing the generated keys.

## CI

A nightly workflow [dwh_parquet.yml](../.github/workflows/dwh_parquet.yml) runs the export
against the staging environment and uploads the manifest along with a sample
Parquet file as artifacts.
