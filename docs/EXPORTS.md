# Exports

Big export endpoints support cursor-based pagination so interrupted downloads can resume.
Each request is capped at **100 000 rows**; when the cap is hit the response includes an
`X-Row-Limit` header and a `Next-Cursor` value to continue from.

Each request caps output to **100k rows**; if hit, the `X-Export-Hint` header advises clients to refine the range and resume with the provided cursor.

Export downloads are provided via tenant-scoped, signed URLs to ensure isolation.

## Owner data export

```
GET /api/outlet/{tenant}/export/all.zip
```

This admin-only endpoint streams a ZIP containing:

- `menu.csv`
- `items.csv`
- `orders.csv`
- `order_items.csv`
- `invoices.csv`
- `payments.csv`
- `customers.csv`
- `settings.json`
- `schema.json` (table names + column metadata)

If 2FA is enabled, a recent `/auth/2fa/stepup` verification is required before accessing this endpoint.

## Resuming

To resume an export, pass the `cursor` query parameter returned from the previous request.

```
GET /api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31&cursor=abc123
```

### Using curl

```bash
# first request
curl -o daily.csv "http://localhost:8000/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31"
# look for the `Next-Cursor` response header

# resume later
curl -o - "http://localhost:8000/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31&cursor=abc123" >> daily.csv
```

## Streaming and resuming in Python

```python
import requests

url = "https://api.example.com/api/outlet/demo/exports/daily"
params = {"start": "2024-01-01", "end": "2024-01-31"}
cursor = None

with open("daily.csv", "ab") as fh:
    while True:
        if cursor:
            params["cursor"] = cursor
        with requests.get(url, params=params, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                fh.write(chunk)
        cursor = r.headers.get("Next-Cursor")
        if not cursor:
            break
```

### Progress via SSE

Provide a `progress` query parameter to the export request and listen on:

```
GET /api/outlet/demo/exports/progress/{progress}
```

Each event reports rows exported so far.

## Helper CLI

A convenience script automates the cursor dance:

```bash
python scripts/export_resume.py \
  --url http://localhost:8000/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31 \
  --output daily.csv
```

If the download stops midway, resume by supplying the last printed cursor:

```bash
python scripts/export_resume.py \
  --url http://localhost:8000/api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31 \
  --output daily.csv \
  --cursor abc123
```

## Progress via SSE

Provide a `job` query parameter when starting an export and listen on the
corresponding progress stream:

```bash
curl -N http://localhost:8000/api/outlet/demo/exports/daily/progress/abc
```

The stream emits `progress` events with the number of rows exported and ends
with a `complete` event.
## Accounting exports

Lightweight CSVs allow hand-off to ledger software without a full integration.

```
GET /api/outlet/{tenant}/accounting/sales_register.csv?from=YYYY-MM-DD&to=YYYY-MM-DD[&composition=true]
GET /api/outlet/{tenant}/accounting/gst_summary.csv?from=YYYY-MM-DD&to=YYYY-MM-DD[&composition=true]

```

### Importing into Tally

1. Download the relevant CSV export.
2. In Tally, navigate to **Gateway of Tally → Import Data → Vouchers**.
3. Choose the CSV file and accept the import prompts.

### Importing into Zoho Books

1. Download the CSV export.
2. In Zoho Books, go to **Sales → Invoices → More Options → Import Invoices**.
3. Upload the file and map the columns as prompted.


