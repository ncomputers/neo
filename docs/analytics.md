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
exported as Prometheus histograms.

