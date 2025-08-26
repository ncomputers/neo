# Secret Rotation Playbook

Regular rotation of sensitive values helps contain the blast radius of a leak and
keeps access hygiene strong.

## Rotation Cadence
- Rotate JWT signing keys, webhook secrets, and VAPID key pairs every 90 days.
- Trigger an immediate rotation if compromise is suspected or a team member leaves.

## Environment Variable Mapping
| Purpose | Current | Next | Previous |
|---------|---------|------|----------|
| JWT auth | `JWT_SECRET` | `JWT_SECRET_NEXT` | `JWT_SECRET_PREV` |
| Webhooks | `WEBHOOK_SIGNING_SECRET` | `WEBHOOK_SIGNING_SECRET_NEXT` | `WEBHOOK_SIGNING_SECRET_PREV` |
| Push notifications | `VAPID_PRIVATE_KEY` / `VAPID_PUBLIC_KEY` | `VAPID_PRIVATE_KEY_NEXT` / `VAPID_PUBLIC_KEY_NEXT` | `VAPID_PRIVATE_KEY_PREV` / `VAPID_PUBLIC_KEY_PREV` |

## Safe Rollout
1. **Prepare** new values without affecting traffic:
   ```bash
   python scripts/rotate_secrets.py prepare <kind>
   ```
2. Deploy with both current and `_NEXT` secrets to warm caches and pods.
3. **Cut over** once new versions are live:
   ```bash
   python scripts/rotate_secrets.py cutover <kind>
   ```
4. Redeploy to pick up the new values.
5. **Purge** old secrets after verification:
   ```bash
   python scripts/rotate_secrets.py purge <kind>
   ```

The `scripts/rotate_secret.py` helper is a placeholder that will eventually wrap
these steps for single-secret workflows.
