# Billing Lifecycle

Tenants subscribe to a plan that grants access for a billing period. Each subscription stores the plan, current period and status. Default plans (Starter, Standard, Pro) are seeded in-memory for now.

## Grace Logic

When a subscription expires the tenant enters a configurable grace period (default 7 days). During grace the product continues to function. Once the grace period elapses, table scans and guest orders are blocked until payment is received. Owners may still visit `/admin/billing` to renew.

## Webhook Security

The mock payment gateway posts events to `/billing/webhook/mock` with an `X-Mock-Signature` header. The body is signed using HMAC-SHA256 with a shared secret. Events are processed idempotently and recorded for audit.

## Swapping Gateways

`BillingGateway` is a small interface with `create_checkout_session`, `verify_webhook` and `list_payments`. A real UPI or payment processor can replace `MockGateway` by implementing the same interface and wiring it into the billing routes.
