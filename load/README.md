# Load Testing

This directory contains basic [Locust](https://locust.io/) scenarios for the guest flow:

1. **View menu** – Performs conditional `GET /g/{table_token}/menu` requests using the `ETag` header to exercise `304 Not Modified` responses.
2. **Place order** – Posts to `/g/{table_token}/order` with a unique `Idempotency-Key` header.
3. **Generate bill** – Fetches `/g/{table_token}/bill` and then reapplies the request with a `coupon` query parameter.

## Usage

Set the target host in `HOST` and optionally override `TABLE_TOKEN`:

```bash
export HOST="http://localhost:8000"
export TABLE_TOKEN="T-001"
locust -f load/locustfile.py
```

The script will spawn virtual users that perform the above actions against the configured host.
