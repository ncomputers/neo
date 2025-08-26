# Order Void Approval Workflow

Two routes control cancellation of orders:

- `POST /api/outlet/{tenant_id}/orders/{order_id}/void/request` – staff submit a void request with a reason.
- `POST /api/outlet/{tenant_id}/orders/{order_id}/void/approve` – managers approve and the order is cancelled with invoice totals adjusted.

Each step is audited and pending requests require approval before stock reversal.
Managers can optionally require step-up 2FA during approval for sensitive cancellations.
