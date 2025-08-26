# Demo Tenant Seeder

Use `scripts/demo_seed.py` to populate a tenant with sample data for quick
local demos.

```bash
python scripts/demo_seed.py --tenant DEMO
```

The command creates a default menu category, a few menu items with placeholder
images stored in `api/app/static/images`, and six tables (`T-001`–`T-006`). The
created identifiers are printed as JSON.

To purge existing categories, items and tables before seeding, pass `--reset`:

```bash
python scripts/demo_seed.py --tenant DEMO --reset
```

## Sandbox Tenant Endpoint

For a quick demo environment, an admin can request a sandbox tenant via the API:

```
POST /api/admin/tenant/sandbox
```

The response returns a `tenant_id` and an `expires_at` timestamp exactly seven
days in the future. The sandbox clones menu and settings without storing any
personally identifiable information and comes with a few demo orders.

Example response:

```json
{
  "data": {
    "tenant_id": "abc123",
    "expires_at": "2030-01-01T12:00:00"
  }
}
```
