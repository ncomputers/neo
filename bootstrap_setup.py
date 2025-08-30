#!/usr/bin/env python3
"""
bootstrap_setup.py — one-shot bootstrap for pilot/staging (idempotent)

What it does:
- Ensures required .env keys (creates/updates .env with sane defaults)
- Verifies Postgres connectivity; creates app DB + demo tenant DB via `psql` if available
- Patches packages/flags tsconfig to fix TypeScript build errors
- Runs seed + QR pack scripts
- Builds monorepo (pnpm -w build)
- Optionally builds Docker image if daemon is available

Usage:
  python3 bootstrap_setup.py --all
  python3 bootstrap_setup.py --env-only
  python3 bootstrap_setup.py --seed-only
  python3 bootstrap_setup.py --build-only
  python3 bootstrap_setup.py --docker
"""
import os
import re
import sys
import json
import shutil
import socket
import subprocess
import time
from pathlib import Path
import uuid

REPO_ROOT = Path(__file__).resolve().parent
ENV_FILE  = REPO_ROOT / ".env"

REQUIRED_ENV_DEFAULTS = {
    # Postgres
    "POSTGRES_SUPER_DSN": os.environ.get("POSTGRES_SUPER_DSN", "postgresql://postgres:postgres@localhost:5432/postgres"),
    "POSTGRES_APP_DB": os.environ.get("POSTGRES_APP_DB", "neo_app"),
    "POSTGRES_TENANT_DSN_TEMPLATE": os.environ.get("POSTGRES_TENANT_DSN_TEMPLATE", "postgresql://postgres:postgres@localhost:5432/neo_tenant_{tenant}"),
    # JWT/Secrets
    "JWT_SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY", f"dev-{uuid.uuid4()}"),
    "JWT_KID": os.environ.get("JWT_KID", "dev-key-1"),
    # Web/App
    "API_BASE": os.environ.get("API_BASE", "http://localhost:8000"),
    "WS_BASE": os.environ.get("WS_BASE", "ws://localhost:8000"),
    "ORIGINS": os.environ.get("ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175"),
    "STAGING_MODE": os.environ.get("STAGING_MODE", "true"),
    # Billing/Referrals
    "REFERRAL_MAX_CREDITS": os.environ.get("REFERRAL_MAX_CREDITS", "5000"),
    "PRORATION_TAX_RATE": os.environ.get("PRORATION_TAX_RATE", "0.18"),
    # Storage
    "STORAGE_DIR": os.environ.get("STORAGE_DIR", str(REPO_ROOT / "storage")),
    # Email sandbox
    "EMAIL_FROM": os.environ.get("EMAIL_FROM", "no-reply@example.local"),
    "EMAIL_SMTP_URL": os.environ.get("EMAIL_SMTP_URL", "smtp://localhost:25"),
}

def log(s: str) -> None:
    print(f"▶ {s}")

def write_env() -> None:
    log(f"Ensuring .env at {ENV_FILE}")
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            existing[k.strip()] = v.strip()
    # Merge but keep any existing values
    updated = dict(REQUIRED_ENV_DEFAULTS)
    updated.update(existing)
    lines = [f"{k}={updated[k]}" for k in REQUIRED_ENV_DEFAULTS.keys()]
    if ENV_FILE.exists():
        backup = ENV_FILE.with_suffix(".env.backup")
        shutil.copy(ENV_FILE, backup)
        log(f"Backed up existing .env to {backup}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    log("Wrote required keys to .env")

def parse_dsn(dsn: str):
    # very loose parse: postgres://user:pass@host:port/db
    m = re.match(r"^\w+://(?P<user>[^:]+):(?P<pw>[^@]+)@(?P<host>[^:/]+):(?P<port>\d+)/(?P<db>[^?]+)", dsn)
    return m.groupdict() if m else None

def check_host_port(host: str, port: str, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False

def have_psql() -> bool:
    return shutil.which("psql") is not None

def run(cmd, cwd=None, check=True, env=None):
    log(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, env=env or os.environ, check=check)

def ensure_db() -> None:
    # Check super DSN host:port
    dsn = os.environ.get("POSTGRES_SUPER_DSN", REQUIRED_ENV_DEFAULTS["POSTGRES_SUPER_DSN"])
    info = parse_dsn(dsn)
    if not info:
        log(f"ERROR: POSTGRES_SUPER_DSN looks invalid: {dsn}")
        sys.exit(2)
    if not check_host_port(info["host"], info["port"]):
        log(f"ERROR: cannot connect to Postgres at {info['host']}:{info['port']}")
        log("Hint: start PostgreSQL or point POSTGRES_SUPER_DSN to a reachable instance.")
        sys.exit(2)

    app_db = os.environ.get("POSTGRES_APP_DB", REQUIRED_ENV_DEFAULTS["POSTGRES_APP_DB"])
    demo_db_dsn = os.environ.get("POSTGRES_TENANT_DSN_TEMPLATE", REQUIRED_ENV_DEFAULTS["POSTGRES_TENANT_DSN_TEMPLATE"]).format(tenant="demo")
    demo_info = parse_dsn(demo_db_dsn)
    demo_db_name = demo_info["db"] if demo_info else "neo_tenant_demo"

    if not have_psql():
        log("WARN: psql not found in PATH. Skipping DB creation. You can run these manually:")
        print(f"""
psql {dsn} -c "CREATE DATABASE {app_db};"
psql {dsn} -c "CREATE DATABASE {demo_db_name};"
""")
        return

    # Create DBs idempotently
    run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c",
         f"DO $$BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname='{app_db}') THEN CREATE DATABASE {app_db}; END IF; END$$;"])
    run(["psql", dsn, "-v", "ON_ERROR_STOP=1", "-c",
         f"DO $$BEGIN IF NOT EXISTS (SELECT FROM pg_database WHERE datname='{demo_db_name}') THEN CREATE DATABASE {demo_db_name}; END IF; END$$;"])
    log("DBs ensured (app + demo tenant)")

def patch_flags_tsconfig() -> None:
    flags_dir = REPO_ROOT / "packages" / "flags"
    tsconfig = flags_dir / "tsconfig.json"
    pkg = flags_dir / "package.json"
    if not flags_dir.exists():
        log("No packages/flags — skipping TS patch")
        return

    # package.json: ensure types/exports fields
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text() or "{}")
        except Exception:
            data = {}
        data.setdefault("types", "dist/index.d.ts")
        data.setdefault("main", "dist/index.js")
        data.setdefault("module", "dist/index.js")
        if "exports" not in data:
            data["exports"] = {
                ".": {
                    "types": "./dist/index.d.ts",
                    "import": "./dist/index.js",
                    "require": "./dist/index.js"
                }
            }
        pkg.write_text(json.dumps(data, indent=2))
        log("Patched packages/flags/package.json")

    # tsconfig: ensure libs & module resolution
    base_compiler = {
        "target": "ES2020",
        "lib": ["ES2020", "DOM"],
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "jsx": "react-jsx",
        "declaration": True,
        "outDir": "dist",
        "strict": True,
        "skipLibCheck": True
    }
    if tsconfig.exists():
        try:
            existing = json.loads(tsconfig.read_text() or "{}")
        except Exception:
            existing = {}
        existing.setdefault("compilerOptions", {})
        existing["compilerOptions"].update(base_compiler)
        existing.setdefault("include", ["src"])
        existing.setdefault("exclude", ["dist", "node_modules"])
        if "extends" not in existing:
            existing["extends"] = "../../packages/config/tsconfig.base.json"
        tsconfig.write_text(json.dumps(existing, indent=2))
    else:
        tsconfig.write_text(json.dumps({
            "extends": "../../packages/config/tsconfig.base.json",
            "compilerOptions": base_compiler,
            "include": ["src"],
            "exclude": ["dist", "node_modules"]
        }, indent=2))
    log("Patched packages/flags/tsconfig.json")

def run_seed_and_qr() -> None:
    env = os.environ.copy()
    env.update({k: v for k, v in REQUIRED_ENV_DEFAULTS.items()})
    # Ensure storage dir
    storage = Path(env["STORAGE_DIR"])
    storage.mkdir(parents=True, exist_ok=True)

    seed = REPO_ROOT / "scripts" / "seed_pilot.py"
    if seed.exists():
        run([sys.executable, str(seed)], env=env)
    else:
        log("WARN: scripts/seed_pilot.py not found; skipping")

    qr = REPO_ROOT / "scripts" / "make_qr_pack.py"
    if qr.exists():
        run([sys.executable, str(qr)], env=env)
    else:
        log("WARN: scripts/make_qr_pack.py not found; skipping")

def pnpm_install_build() -> None:
    if shutil.which("pnpm") is None:
        log("ERROR: pnpm not found. Install: npm i -g pnpm")
        sys.exit(2)
    run(["pnpm", "-w", "install"])
    run(["pnpm", "-w", "build"])

def docker_build() -> None:
    if shutil.which("docker") is None:
        log("WARN: docker not installed or not in PATH; skipping image build")
        return
    try:
        subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        log("WARN: Cannot connect to Docker daemon. Fix with:\n"
            "  sudo usermod -aG docker $USER && newgrp docker\n"
            "  sudo systemctl enable --now docker\n")
        return
    tag = os.environ.get("UI_IMAGE_TAG", "your/ui:pilot")
    dockerfile = REPO_ROOT / "Dockerfile.ui"
    if not dockerfile.exists():
        log("WARN: Dockerfile.ui not found; skipping docker build")
        return
    run(["docker", "build", "-f", str(dockerfile), "-t", tag, "."])

def main():
    args = set(sys.argv[1:])
    if not args or "--all" in args:
        write_env()
        ensure_db()
        patch_flags_tsconfig()
        pnpm_install_build()
        run_seed_and_qr()
        docker_build()
        log("✅ All done.")
        return
    if "--env-only" in args:
        write_env(); ensure_db(); return
    if "--seed-only" in args:
        run_seed_and_qr(); return
    if "--build-only" in args:
        patch_flags_tsconfig(); pnpm_install_build(); return
    if "--docker" in args:
        docker_build(); return
    print(__doc__)

if __name__ == "__main__":
    main()
