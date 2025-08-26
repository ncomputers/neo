# Optional Product Analytics

Minimal event tracking can be sent to [PostHog](https://posthog.com) or
[Mixpanel](https://mixpanel.com). Analytics is disabled by default and only
records data for tenants that have granted consent.

## Enabling

1. Turn on the feature flag:

   ```bash
   export FLAG_ANALYTICS=1
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

