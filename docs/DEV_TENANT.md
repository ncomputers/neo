# Development Tenant Quickstart

Use the following commands to create and initialize a demo tenant for local development.
Run each command from the project root:

1. Create the tenant database
   ```bash
   python scripts/tenant_create_db.py --tenant demo
   ```
2. Apply database migrations
   ```bash
   python scripts/tenant_migrate.py --tenant demo
   ```
3. Seed the database with demo data
   ```bash
   python scripts/tenant_seed.py --tenant demo
   ```

4. (Optional) Create demo hotel rooms
   ```bash
   python scripts/tenant_seed_hotel.py --tenant demo
   ```

5. (Optional) Create a demo takeaway counter
   ```bash
   python scripts/tenant_seed_counter.py --tenant demo
   ```

6. (Optional) Seed a large dataset for load testing
   ```bash
   POSTGRES_TENANT_DSN_TEMPLATE=sqlite+aiosqlite:///tmp/{tenant_id}.db \\
   python scripts/seed_large_outlet.py --tenant demo \\
       --items 5000 --tables 300 --orders 50000

   ```

These commands set up a fully initialized `demo` tenant ready for development.
