#!/usr/bin/env python3
"""
One-command runner for the Neo monorepo.

Features:
- --install  : create .venv and install backend deps; install PWA deps
- --run      : start FastAPI (uvicorn) and PWA (vite) together; watches and prints logs
- --test     : run backend tests with pytest
- --docker   : (optional) bring up docker services from ops/docker-compose.yml
- --env      : copy .env.example to .env if missing
- --all      : setup env, install deps, start Docker, run tests, and launch services

Examples:
  python run_all.py --install --env
  python run_all.py --run
  python run_all.py --test
  python run_all.py --docker --run
  python run_all.py --all
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
PWA_DIR = ROOT / "pwa"
OPS_DIR = ROOT / "ops"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
VENV_DIR = ROOT / ".venv"
APPS_DIR = ROOT / "apps"
SPA_APPS = ["guest", "admin", "kds"]


def run(cmd, cwd=None, env=None, check=True):
    print(f"\n$ {' '.join(cmd)}  (cwd={cwd or ROOT})")
    return subprocess.run(
        cmd, cwd=cwd or ROOT, env=env or os.environ.copy(), check=check
    )


def ensure_python_venv():
    if VENV_DIR.exists():
        print(f"✅ Using existing virtualenv: {VENV_DIR}")
        return
    print("🔧 Creating virtualenv in .venv ...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])
    print("✅ Virtualenv created.")


def pip_exe():
    if platform.system() == "Windows":
        return str(VENV_DIR / "Scripts" / "pip.exe")
    return str(VENV_DIR / "bin" / "pip")


def python_exe():
    if platform.system() == "Windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def which(cmd):
    return shutil.which(cmd)


def vite_port():
    port = os.environ.get("VITE_PORT")
    if port:
        return port
    cfg = ROOT / "packages" / "config" / "vite.cjs"
    if cfg.exists():
        match = re.search(r"port:\s*(\d+)", cfg.read_text())
        if match:
            return match.group(1)
    return "5173"


def install_backend():
    ensure_python_venv()
    pip = pip_exe()
    req = API_DIR / "requirements.txt"
    if not req.exists():
        print("⚠️ api/requirements.txt not found. Skipping backend install.")
        return
    print("📦 Installing backend dependencies ...")
    run([pip, "install", "-U", "pip", "wheel", "setuptools>=78.1.1"])
    run([pip, "install", "-r", str(req)])
    print("✅ Backend deps installed.")


def install_frontend():
    if not (PWA_DIR / "package.json").exists():
        print("⚠️ pwa/package.json not found. Skipping frontend install.")
        return
    node = which("node")
    npm = which("npm")
    if not (node and npm):
        print("⚠️ Node.js/npm not found on PATH. Skipping PWA install.")
        return
    print("📦 Installing PWA dependencies ...")
    run(["npm", "install"], cwd=PWA_DIR)
    print("✅ PWA deps installed.")


def build_spas():
    pnpm = which("pnpm")
    if not pnpm:
        print("⚠️ pnpm not found. Skipping SPA build.")
        return
    for app in SPA_APPS:
        dist = APPS_DIR / app / "dist"
        if dist.exists():
            print(f"✅ {app} SPA already built.")
            continue
        print(f"🏗️ Building {app} SPA ...")
        run([pnpm, "--filter", f"@neo/{app}", "build"])
    print("✅ SPA builds complete.")


def copy_env_if_needed():
    if ENV_FILE.exists():
        print("✅ .env already exists.")
        return
    if ENV_EXAMPLE.exists():
        print("📝 Creating .env from .env.example ...")
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print("✅ .env created. Review and edit values as needed.")
    else:
        print("⚠️ No .env.example found; skipping.")


def run_docker_compose():
    dc_yml = OPS_DIR / "docker-compose.yml"
    if not dc_yml.exists():
        print("⚠️ ops/docker-compose.yml not found. Skipping Docker.")
        return
    docker = which("docker")
    if not docker:
        print("⚠️ Docker not installed or not on PATH.")
        return
    # Prefer `docker compose` if available
    try:
        run(["docker", "compose", "up", "-d"], cwd=OPS_DIR)
    except subprocess.CalledProcessError:
        if which("docker-compose"):
            run(["docker-compose", "up", "-d"], cwd=OPS_DIR)
        else:
            raise
    print(
        "✅ Docker services started (postgres, redis, minio, proxy, api if configured)."
    )


def start_processes():
    build_spas()
    # Backend: uvicorn api.app.main:app
    uvicorn = [
        python_exe(),
        "-m",
        "uvicorn",
        "api.app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",  # nosec B104
        "--port",
        "8000",
    ]
    # Frontend: vite in pwa
    vite_cmd = ["npm", "run", "dev"]

    procs = []

    print("🚀 Starting FastAPI on http://localhost:8000 ...")
    procs.append(subprocess.Popen(uvicorn, cwd=ROOT))

    vite_port_num = vite_port()
    if (PWA_DIR / "package.json").exists() and which("npm"):
        print(f"🌐 Starting PWA (Vite) on http://localhost:{vite_port_num} ...")
        procs.append(subprocess.Popen(vite_cmd, cwd=PWA_DIR))
    else:
        print("ℹ️ Skipping PWA (missing package.json or npm).")

    try:
        for p in procs:
            print(f"▶️ PID {p.pid} started.")
        print("\nPress Ctrl+C to stop both services.\n")

        while procs:
            for p in list(procs):
                code = p.poll()
                if code is None:
                    continue
                if code != 0:
                    print(
                        f"❌ Process {p.pid} exited with code {code}. Stopping others..."
                    )
                    for other in procs:
                        if other is not p and other.poll() is None:
                            other.terminate()
                    for other in procs:
                        if other.poll() is None:
                            try:
                                other.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                other.kill()
                    raise SystemExit(code)
                else:
                    procs.remove(p)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Stopping services ...")
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        print("✅ Stopped.")


def run_tests():
    ensure_python_venv()
    install_backend()
    pip = pip_exe()
    # Ensure pytest present (api/requirements.txt already includes it, but be safe)
    run([pip, "install", "pytest"])

    env = os.environ.copy()
    if "PGDATABASE" not in env:
        env["PGDATABASE"] = "testdb"
        print("ℹ️ PGDATABASE not set, defaulting to 'testdb'")

    if not which("docker"):
        print("⚠️ Docker not installed or not on PATH. Skipping test DB bootstrap.")
    else:
        bootstrap = ROOT / ".ci" / "scripts" / "bootstrap_test_db.sh"
        bootstrap.chmod(bootstrap.stat().st_mode | 0o111)
        print("📦 Bootstrapping test database ...")
        run([str(bootstrap)], env=env)

    print("🧪 Running backend tests ...")
    run([python_exe(), "-m", "pytest", "-q"], cwd=API_DIR, env=env)


def main():
    parser = argparse.ArgumentParser(
        description="Run and test the Neo monorepo from one script."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install backend and frontend dependencies",
    )
    parser.add_argument(
        "--run", action="store_true", help="Run FastAPI and PWA together"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run backend tests with pytest"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Start docker services from ops/docker-compose.yml",
    )
    parser.add_argument(
        "--env", action="store_true", help="Copy .env.example to .env if missing"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Run env setup, install deps, start Docker, run tests, and launch services"
        ),
    )
    args = parser.parse_args()
    if args.all:
        copy_env_if_needed()
        install_backend()
        install_frontend()
        run_docker_compose()
        run_tests()
        start_processes()
        return

    if args.env:
        copy_env_if_needed()
    if args.install:
        install_backend()
        install_frontend()
    if args.docker:
        run_docker_compose()
    if args.test:
        run_tests()
    if args.run:
        start_processes()

    if not any([args.install, args.run, args.test, args.docker, args.env, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
