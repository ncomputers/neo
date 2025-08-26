# BI Parquet Dumps

The `scripts/bi_dump.py` helper exports orders, order items and payments for a
specified day as Parquet files partitioned by date. The files are uploaded to an
S3-compatible bucket along with a manifest JSON describing the dump.

## Configuration

Set the following environment variables:

- `BI_DB_DSN` – Database DSN for the tenant data
- `BI_S3_ENDPOINT`, `BI_S3_REGION` – S3 connection details
- `BI_S3_BUCKET` – Destination bucket
- `BI_S3_ACCESS_KEY`, `BI_S3_SECRET_KEY` – Credentials for the bucket
- `BI_TMP_DIR` – Optional temp directory (defaults to `/tmp`)

Each run uploads Parquet files under `<dataset>/d=<YYYY-MM-DD>/` and writes a
manifest to `manifest/<YYYY-MM-DD>.json` listing the generated keys.
