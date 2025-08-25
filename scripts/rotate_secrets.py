#!/usr/bin/env python3
"""Rotate sensitive environment variables without downtime."""

from __future__ import annotations

import argparse
import base64
import os
import secrets
from pathlib import Path
from typing import Dict

import requests

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

ENV_FILE = Path(os.environ.get("ENV_FILE", ".env"))


def require_stepup() -> None:
    base = os.environ.get("API_BASE_URL")
    token = os.environ.get("API_TOKEN")
    if not base or not token:
        return
    code = input("2FA code: ")
    resp = requests.post(
        f"{base}/auth/2fa/stepup",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise SystemExit("2FA step-up required")


def load_env(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v
    return data


def write_env(path: Path, data: Dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in sorted(data.items())]
    lines.append("")
    path.write_text("\n".join(lines))


def gen_secret() -> str:
    return secrets.token_urlsafe(32)


def gen_vapid() -> Dict[str, str]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    priv = private_key.private_numbers().private_value.to_bytes(32, "big")
    pub = private_key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return {
        "VAPID_PRIVATE_KEY": base64.urlsafe_b64encode(priv).decode().rstrip("="),
        "VAPID_PUBLIC_KEY": base64.urlsafe_b64encode(pub).decode().rstrip("="),
    }


def prepare(env: Dict[str, str], kind: str) -> None:
    if kind == "jwt":
        env["JWT_SECRET_NEXT"] = gen_secret()
    elif kind == "webhook":
        env["WEBHOOK_SIGNING_SECRET_NEXT"] = gen_secret()
    elif kind == "vapid":
        pair = gen_vapid()
        env["VAPID_PRIVATE_KEY_NEXT"] = pair["VAPID_PRIVATE_KEY"]
        env["VAPID_PUBLIC_KEY_NEXT"] = pair["VAPID_PUBLIC_KEY"]
    else:
        raise ValueError("unknown kind")


def cutover(env: Dict[str, str], kind: str) -> None:
    if kind == "jwt":
        _cutover(env, "JWT_SECRET")
    elif kind == "webhook":
        _cutover(env, "WEBHOOK_SIGNING_SECRET")
    elif kind == "vapid":
        _cutover(env, "VAPID_PRIVATE_KEY")
        _cutover(env, "VAPID_PUBLIC_KEY")
    else:
        raise ValueError("unknown kind")


def _cutover(env: Dict[str, str], base: str) -> None:
    nxt = f"{base}_NEXT"
    prev = f"{base}_PREV"
    if nxt not in env:
        raise KeyError(f"{nxt} not set")
    if base in env:
        env[prev] = env[base]
    env[base] = env.pop(nxt)


def purge(env: Dict[str, str], kind: str) -> None:
    if kind == "jwt":
        env.pop("JWT_SECRET_PREV", None)
    elif kind == "webhook":
        env.pop("WEBHOOK_SIGNING_SECRET_PREV", None)
    elif kind == "vapid":
        env.pop("VAPID_PRIVATE_KEY_PREV", None)
        env.pop("VAPID_PUBLIC_KEY_PREV", None)
    else:
        raise ValueError("unknown kind")


def main() -> None:
    require_stepup()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "cutover", "purge"])
    parser.add_argument("kind", choices=["jwt", "webhook", "vapid"])
    parser.add_argument("--env-file", default=str(ENV_FILE))
    args = parser.parse_args()

    path = Path(args.env_file)
    env = load_env(path)

    if args.action == "prepare":
        prepare(env, args.kind)
    elif args.action == "cutover":
        cutover(env, args.kind)
    elif args.action == "purge":
        purge(env, args.kind)
    write_env(path, env)
    print(f"{args.action} complete for {args.kind}")


if __name__ == "__main__":
    main()
