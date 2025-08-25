# Exports

Big export endpoints support cursor-based pagination so interrupted downloads can resume.

## Resuming

To resume an export, pass the `cursor` query parameter returned from the previous request.

```
GET /api/outlet/demo/exports/daily?start=2024-01-01&end=2024-01-31&cursor=abc123
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

