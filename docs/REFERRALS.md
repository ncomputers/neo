# Referrals Program

This document describes the referral program where existing outlets invite other outlets and earn billing credits when the referred outlet becomes a paying customer.

## Data model
- **referrals**(id, referrer_tenant_id, code, landing_url, clicks, signups, converted, created_at)
- **referral_credits**(id, tenant_id, amount_inr, reason, applied_invoice_id NULL, created_at)
- `subscriptions.credit_balance_inr` numeric(10,2) default 0

## Flow
1. Generate referral code at `/admin/referrals`.
2. Landing page `/signup?ref=CODE` stores attribution as `referred_tenant_id`.
3. When the referred tenant pays their first invoice (`status=PAID`), create `referral_credits` for the referrer and apply to the next invoice after computing GST on the post-credit taxable amount.

## Guardrails
- Cap credits per referrer with env `REFERRAL_MAX_CREDITS` (₹5000).
- Block self-referral using owner email/phone.
- Rate‑limit signups per IP.
- Referred invoice must be at least `plan.price_inr`.
- Idempotent conversion handling for subscription events.

## API
- `GET /admin/referrals`
- `POST /admin/referrals/new`
- `GET /referral/landing?ref=CODE`
- internal `apply_credit_to_invoice(subscription, amount)`

## Emails
- "Your referral converted" email to referrer with credit amount.
- "Welcome (referred)" email with onboarding checklist.

## Tests
- End-to-end: referral link → signup → paid → credit created and applied.
- Credit application math (rounding; tax on net).
- Fraud blocks (self, cap, duplicate).

## Example
Outlet A shares its referral link. Outlet B signs up using the link, pays the first invoice, and Outlet A receives referral credits automatically applied to the next bill.
