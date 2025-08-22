# Product Requirements Document (PRD) — QR-based Dine‑in Ordering SaaS
**Version:** 1.0

## 1. Vision & Goals
A lightweight, paperless, QR-based dine‑in ordering & billing system for small restaurants/hotels, optimized for low training effort and offline/hybrid reliability.

## 2. In‑Scope (MVP)
- Fixed table QR → menu → multi‑round ordering → single consolidated bill.
- Statuses: Placed → Accepted → In‑Progress → Ready → Served → Cancelled (optional Rejected/Hold).
- UPI & Cash payments; Card optional. Deep‑link + static QR.
- GST modes: Unregistered / Composition / Registered (B2C default, optional B2B).
- EMA‑based ETA (outlet‑wide over last 10/20 orders).
- Roles: Super‑Admin, Outlet Admin/Manager, Cashier, Kitchen, Cleaner (PIN login for staff).
- KDS (item‑level and/or whole‑order accept/serve; configurable).
- Stock toggle (Out of Stock hides items).
- Daily closing report (Z‑report) with email/WhatsApp and CSV/Excel export.
- Subscription: per table/month; 7‑day grace; block new orders after expiry.
- Multi‑tenant SaaS: master DB + separate DB per outlet.
- Hybrid/offline: local node + cloud sync.
- Audit logging; IP rate‑limit + auto‑block after 3 rejections; table lock until cleaning.
- Languages: English default; optional locales.

## 3. Out of Scope (MVP)
Reservations/waitlist; complex item modifiers; multi‑station routing; native apps; PSP webhooks auto‑verify (future).

## 4. Users & Needs
- **Guest:** quick menu, place order, see live status, request bill, pay.
- **Kitchen:** simple KDS, swipe actions, color‑timers, sounds, out‑of‑stock toggle.
- **Cashier/Admin:** run bills, discounts/tips/coupons, payments, settlement, reports.
- **Cleaner:** lock/unlock table after settlement.
- **Super‑Admin:** onboard outlets, plans, domains/SSL, health, backups.

## 5. Constraints
- Self‑hosted Linux friendly; low compute footprint on local node (RPi/mini‑PC).
- India default: INR, IST; UPI primary method.
- Price lock per session; price changes apply only on next QR session.

## 6. KPIs
- Time from scan→order (< 60s median).
- Order to Accept SLA (< 2 min 90th).
- KDS throughput (orders/hour).
- Payment settlement accuracy (100%).
- Uptime (cloud ≥ 99.5%; local node ≥ 99%).
- Onboarding time per outlet (< 60 min including QR prints).

## 7. Acceptance Criteria (high‑level)
- End‑to‑end happy path works (QR→order→KDS→bill→UPI/Cash settle→lock→clean unlock).
- GST invoice correct per mode; rounding applied.
  - Regular: HSN per line, CGST/SGST split, GSTIN header.
  - Composition: hide HSN, single "Composition Tax Included", GSTIN + Composition Scheme.
  - Unregistered: hide all GST fields, show tax-exempt note.
- Subscription guard and grace logic enforced.
- Offline orders queue and sync correctly.
