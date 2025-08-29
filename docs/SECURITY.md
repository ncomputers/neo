# Security

## HTTP Headers
- `Content-Security-Policy`: `default-src 'self'; script-src 'self' 'nonce-{RANDOM}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://YOUR_API https://YOUR_WS; frame-ancestors 'self'`
- `Strict-Transport-Security`: `max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options`: `nosniff`
- `Referrer-Policy`: `strict-origin-when-cross-origin`
- `Permissions-Policy`: `geolocation=(), microphone=(), camera=(), notifications=(self)`
- `X-Frame-Options`: `SAMEORIGIN`

CSP reports are sent to `/csp/report` when `Content-Type` is HTML.

### Adding Origins
Allowed origins are configured via the `ALLOWED_ORIGINS` environment variable (comma separated).

Our security contact is published at `/.well-known/security.txt`.

## Token Rotation
- Access tokens expire after 15 minutes.
- Rotate signing keys and expose JWKS at `/auth/jwks.json`.

## Incident Response
1. Rotate credentials.
2. Invalidate active sessions.
3. Review audit logs.
