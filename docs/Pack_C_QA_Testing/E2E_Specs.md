# E2E Specs (Playwright-style)

## Guest Happy Path
- Scan QR → Menu → Add 2 items → Place → See status → Get Bill → Pay (cash) → Thank you → Rating.

## Multi-round Ordering
- Place first order → Served → Add more items → Get final consolidated bill → Pay UPI.

## KDS Flow
- Order appears instantly → Accept (whole) → Ready → Served → Status reflected to guest.

## Offline/Online
- Disconnect WAN → place order on LAN → reconnect → verify sync, invoice numbering preserved.

## Subscription Block
- Expire subscription past grace → verify new orders blocked; renewal banner shows.
