# Two-Factor Authentication

The API supports optional Time-based One-Time Password (TOTP) two-factor authentication for owner and admin accounts.

## Endpoints

* `POST /auth/2fa/setup` – create a new TOTP secret and return an `otpauth://` URI along with a QR code.
* `POST /auth/2fa/enable` – confirm setup by providing a valid TOTP code.
* `POST /auth/2fa/disable` – disable 2FA using either a TOTP or backup code.
* `POST /auth/2fa/verify` – verify a TOTP or backup code during login. Requests are rate limited.
* `GET /auth/2fa/backup` – generate ten one-time backup codes.

Secrets and backup codes are stored hashed in the database. All actions are audit logged.
