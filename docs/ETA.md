# ETA model

The ETA service estimates when an order will be ready.

## Formula

```
ETA = max(base_item_eta * queue_factor) + buffer
```

`base_item_eta` is taken from nightly aggregated prep statistics (p50 or p80
per configuration). If no data exists a global fallback of 10 minutes is used.

The queue factor increases linearly with the number of active tickets and is
capped by `MAX_QUEUE_FACTOR`.

## Configuration

- `PREP_SLA_MIN` – default prep time in minutes.
- `ETA_CONFIDENCE` – percentile used (`p50` or `p80`).
- `MAX_QUEUE_FACTOR` – upper bound for the queue multiplier.
- `ETA_ENABLED` – feature flag controlling exposure of the endpoint.

## SLA widgets

Owner dashboards show the 7‑day SLA hit rate and average lateness to highlight
kitchen performance.
