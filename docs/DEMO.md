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
