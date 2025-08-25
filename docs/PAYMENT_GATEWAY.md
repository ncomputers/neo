# Payment Gateway

Optional Razorpay/Stripe checkout can be enabled per deployment.

## Enable

1. Set environment variable `ENABLE_GATEWAY=true` for the API service.
2. In the master database, set `gateway_provider` for the tenant to either `razorpay` or `stripe`.
   When unset or `none`, the application falls back to manual UPI/UTR flow.

## Test mode

Gateways usually provide a sandbox environment. Configure your Razorpay/Stripe
credentials for test mode and trigger checkout:

```bash
curl -X POST https://localhost:8000/api/outlet/demo/checkout/start \
     -H 'Content-Type: application/json' \
     -d '{"invoice_id": 1, "amount": 10}'
```

Use the gateway dashboard to simulate the webhook call back to
`/api/outlet/<tenant>/checkout/webhook` with a valid signature.
