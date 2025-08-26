# Guest Receipts

Guests who share their email or phone number and opt in can view recent bills
through a lightweight receipt vault.

- `GET /guest/receipts?phone=XXXXXXXXXX` – list the last ten redacted
  receipts for the supplied contact. Use `email=` instead of `phone` to look up
  by email address.
- Only minimal bill totals are retained. Line level details and tax breakdowns
  are stripped before storage.
- Receipts are held for ``guest_receipts_ttl_days`` (30 days by default) unless
  a tenant configures a longer retention period.

