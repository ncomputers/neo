# Optional Product Analytics

Minimal event tracking can be sent to [PostHog](https://posthog.com) or
[Mixpanel](https://mixpanel.com). Analytics is disabled by default and only
records data for tenants that have granted consent. Events are buffered and
sent in small batches with automatic retries.

## Enabling

1. Enable analytics:

   ```bash
   export TENANT_ANALYTICS_ENABLED=1
   ```

2. Supply credentials for either PostHog or Mixpanel:

   - **PostHog** – set `POSTHOG_API_KEY` and optional `POSTHOG_HOST`.
   - **Mixpanel** – set `MIXPANEL_TOKEN`.

3. Allow specific tenants by listing their IDs in `ANALYTICS_TENANTS`:

   ```bash
   export ANALYTICS_TENANTS="tenant_a,tenant_b"
   ```

Only tenants in this comma-separated list have their events recorded. Common
PII fields such as `email`, `phone` and `name` are removed from event
properties before transmission.

Currently the backend emits a `feedback_submitted` event whenever a guest NPS
entry is stored.

Guest opt-ins for analytics and WhatsApp updates are persisted via the `/g/consent`
endpoint and stored against the customer's record.

## Web Vitals RUM

When the `analytics` feature flag is enabled and a guest or admin has granted
consent, the PWA reports [Web Vitals](https://web.dev/vitals/) for each route
without using any third-party libraries. Largest Contentful Paint (LCP),
Cumulative Layout Shift (CLS), Interaction to Next Paint (INP) and Time to
First Byte (TTFB) are POSTed to `/rum/vitals` along with the current route and
exported as Prometheus histograms. Clients **must** include the `X-Tenant-ID`
header in these requests. The PWA adds this automatically when the
`VITE_TENANT_ID` build-time variable is set:

```sh
VITE_TENANT_ID=<tenant> npm run build
```

The value will be sent as `X-Tenant-ID` in all API calls including the RUM
endpoint.

### Grafana dashboard

`deploy/dashboards/rum.json` defines a Grafana dashboard with panels for
Largest Contentful Paint (LCP), Cumulative Layout Shift (CLS) and Interaction to
Next Paint (INP). Each panel charts the p50, p75 and p95 percentiles per route
using the Prometheus histograms. Import the JSON through Grafana's **Dashboards →
Import** page to load it.

The percentile panels help interpret performance: p50 is the median, p75 shows
upper-quartile latencies and p95 highlights worst-case routes.

### Sample PromQL

Percentiles can be queried directly with `histogram_quantile`:

```promql
histogram_quantile(0.95, sum(rate(web_vitals_lcp_seconds_bucket{route="/"}[5m])) by (le))
histogram_quantile(0.95, sum(rate(web_vitals_cls_bucket{route="/"}[5m])) by (le))
histogram_quantile(0.95, sum(rate(web_vitals_inp_seconds_bucket{route="/"}[5m])) by (le))
```

Replace `0.95` with `0.50` or `0.75` for other percentiles.

