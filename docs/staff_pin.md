# Staff PIN Management

## Set PIN

`POST /api/outlet/{tenant}/staff/{staff_id}/set_pin`

Body: `{ "pin": "1234" }`

Requires `admin` or `manager` staff token. Updates the staff member's PIN,
clears any login throttle for that staff member, and records the change in the
audit log.

## Login Throttling

Staff PIN logins are limited to **5 failed attempts per 10 minutes** for each
combination of IP address and staff code. Once the limit is exceeded the
endpoint responds with `err("AUTH_THROTTLED")` and HTTP 403. Resetting the PIN
via the above endpoint clears the throttle.
