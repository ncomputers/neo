# Security & Threat Model (STRIDE)

## Threats & Mitigations
- **Spoofed Orders (Tampering):** Opaque table tokens, one active session per table; server validates table lock; audit.
- **PIN Brute Force (Repudiation):** Attempt throttling, lockout, salted+hashed PINs.
- **DoS / Abuse (DoS):** Sliding-window rate limit; IP block after 3 rejections; CAPTCHA optional later.
- **Data Exposure (Information Disclosure):** TLS everywhere; JWT scopes; least-privilege; PII minimization.
- **Elevation of Privilege:** RBAC middleware; per-role route guards; audit changes.
- **Integrity:** Price snapshots at order time; invoices immutable post-settlement.

## Secrets
- Stored in env/secret manager; rotate regularly.
