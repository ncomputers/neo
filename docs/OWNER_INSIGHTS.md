# Weekly Owner Insights

This report provides a week over week summary of key restaurant metrics.
Every Monday at 09:00 IST an email is sent to opted-in owners with a
brief HTML summary alongside CSV and PDF attachments for deeper analysis.

## Metrics

- **Gross sales** – total revenue including taxes and charges.
- **Orders** – number of completed orders.
- **Average order value (AOV)** – gross sales divided by orders.
- **Cancellations** – orders cancelled after placement.
- **Preparation time p50/p95** – median and 95th percentile of kitchen prep time.
- **ETA SLA hit rate** – percentage of orders served within the expected time.
- **Top items** – top ten items by quantity and revenue.
- **Coupons used** – count of orders that used a coupon.
- **Referral conversions** – orders placed via referral links.
- **Table turn time** – average duration between seat and bill (if available).

Deltas compare the last seven days against the previous seven.

## Customisation

The script `scripts/owner_insights.py` accepts a `--tenant` argument for a
specific tenant or `all` to process every tenant. Start the report from a
particular week using `--week_start YYYY-MM-DD`.

## Interpretation

Arrows in the report highlight the direction of change compared to the
previous week. Use the insights section to spot anomalies or optimisation tips
for operations, menu and marketing.
