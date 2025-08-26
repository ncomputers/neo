# Device Security

## Register Device

`POST /admin/devices/register`

Body: `{ "name": "Front Tablet", "fingerprint": "abc123" }`

Requires a `manager` or `super_admin` token. Adds the device to the registry and
writes an audit log entry.

## List Devices

`GET /admin/devices`

Returns all registered devices. Requires `manager` or `super_admin` token.

## Unlock PIN

`POST /admin/staff/{username}/unlock_pin`

Clears the PIN lockout state for `username` after too many failed attempts.
Requires `manager` or `super_admin` token and is audited.
