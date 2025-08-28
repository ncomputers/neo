# Billing Lifecycle

Tenants subscribe to a plan that grants access for a billing period. Each subscription stores the plan, current period and status. Default plans (Starter, Standard, Pro) are seeded in-memory for now.

## Grace Logic

When a subscription expires the tenant enters a configurable grace period (default 7 days). During grace the product continues to function. Once the grace period elapses, table scans and guest orders are blocked until payment is received. Owners may still visit `/admin/billing` to renew.

## Webhook Security

The mock payment gateway posts events to `/billing/webhook/mock` with an `X-Mock-Signature` header. The body is signed using HMAC-SHA256 with a shared secret. Events are processed idempotently and recorded for audit.

## Swapping Gateways

`BillingGateway` is a small interface with `create_checkout_session`, `verify_webhook` and `list_payments`. A real UPI or payment processor can replace `MockGateway` by implementing the same interface and wiring it into the billing routes.

## License enforcement

Tenant access is gated based on subscription expiry. The middleware resolves the tenant and classifies the license status:

| Status  | Description                              | Allowed routes                          |
|---------|------------------------------------------|-----------------------------------------|
| ACTIVE  | Current period valid                     | All routes                              |
| GRACE   | Expired but within grace window          | Reads and writes, banner shown          |
| EXPIRED | Beyond grace period                      | Read-only views; writes return HTTP 402 |

Billing endpoints such as `/admin/billing/*` and `/billing/webhook/*` bypass the gate so owners can always renew.

## Plan changes & proration

Upgrading a plan mid-cycle results in a prorated charge for the remaining
period. The proration is computed from the price difference, scaled by the
unused portion of the current period and split into CGST/SGST or IGST as
appropriate.

Examples:

- ₹3000/mo → ₹5000/mo halfway through the cycle (`factor = 0.5`) results in a
  prorated amount of ₹1000 plus 18% GST.
- ₹5000/mo → ₹3000/mo is scheduled for the next renewal. A credit note is
  issued only if the downgrade policy is set to immediate credits.

![Proration preview](img/billing-proration-preview.png)
