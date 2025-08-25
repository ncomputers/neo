# Staff PIN Management

## Set PIN

`POST /api/outlet/{tenant}/staff/{staff_id}/set_pin`

Body: `{ "pin": "1234" }`

Requires `admin` or `manager` staff token. Updates the staff member's PIN,
clears any login lock for that staff member, and records the change in the
audit log including the acting staff ID and role along with the target staff
member.

## Login Lockout

Staff PIN logins are locked for **15 minutes** after **5 failed attempts** for
each combination of IP address and staff code. Once locked the endpoint
responds with `err("AUTH_LOCKED")` and HTTP 403. Unlocking events as well as
lockouts are written to the audit log. Resetting the PIN via the above endpoint
also clears any lockout state.

## PIN Rotation

Staff PINs must be rotated every **90 days**. Logins using a PIN older than 90
days are rejected with HTTP 403 and `PIN expired`. After 80 days logins still
succeed but include `"rotation_warning": true` in the response payload.
