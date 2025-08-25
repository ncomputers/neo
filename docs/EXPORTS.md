# Exports

Big export endpoints support cursor-based pagination so interrupted downloads can resume.

## Owner data export

```
GET /api/outlet/{tenant}/export/all.zip
```

This admin-only endpoint streams a ZIP containing CSV files for menu, orders,
invoices, payments, customers and settings, along with a `schema.json` manifest.

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

