# Payment Gateway

Optional Razorpay/Stripe checkout can be enabled per deployment.

## Enable

1. Set environment variable `ENABLE_GATEWAY=true` for the API service.
2. In the master database, set `gateway_provider` for the tenant to either `razorpay` or `stripe`.
   When unset or `none`, the application falls back to manual UPI/UTR flow.

Set `GATEWAY_SANDBOX=true` to use sandbox credentials globally or set
`gateway_sandbox=true` for an individual tenant.

## Test mode

Configure Razorpay/Stripe credentials for the appropriate environment. When in
sandbox mode, use the `*_SECRET_TEST` variables and trigger checkout:

```bash
curl -X POST https://localhost:8000/api/outlet/demo/checkout/start \
     -H 'Content-Type: application/json' \
     -d '{"invoice_id": 1, "amount": 10}'
```

Use the gateway dashboard to simulate the webhook call back to
`/api/outlet/<tenant>/checkout/webhook` with a valid signature.

### Happy path

1. Call `checkout/start` to obtain an `order_id`.
2. Post a `paid` webhook with HMAC of `order_id|invoice_id|amount|paid`.
   Duplicate webhooks return `attached: False` and do not create a second
   payment.
3. Post a `refund` webhook with HMAC of `order_id|invoice_id|amount|refund` to
   reset the invoice's `settled` status.
