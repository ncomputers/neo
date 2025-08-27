import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import requests

STATUS_FILE = Path(__file__).resolve().parents[2] / "status.json"
API_URL = os.environ.get("STATUS_API_URL", "http://localhost:8000")
API_TOKEN = os.environ.get("STATUS_API_TOKEN")


def _read_status() -> Dict[str, Any]:
    with STATUS_FILE.open() as f:
        return json.load(f)


def _write_status(data: Dict[str, Any]) -> None:
    with STATUS_FILE.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _post_status(data: Dict[str, Any]) -> None:
    payload = {
        "state": data.get("state"),
        "message": data.get("message"),
        "components": data.get("components", []),
    }
    if "incidents" in data:
        payload["incidents"] = data["incidents"]
    headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
    try:
        requests.post(f"{API_URL}/admin/status", json=payload, headers=headers, timeout=5)
    except Exception:
        pass


def start_incident(title: str, details: str) -> None:
    data = _read_status()
    data["state"] = "degraded"
    data["message"] = details
    incidents = data.setdefault("incidents", [])
    incidents.append(
        {
            "title": title,
            "details": details,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    _post_status(data)
    _write_status(data)


def resolve_incident(title: str) -> None:
    data = _read_status()
    incidents = [i for i in data.get("incidents", []) if i.get("title") != title]
    data["incidents"] = incidents
    data["state"] = "degraded" if incidents else "ok"
    if not incidents:
        data["message"] = None
    _post_status(data)
    _write_status(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage status.json incidents")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start = sub.add_parser("start", help="start an incident")
    start.add_argument("title")
    start.add_argument("details")

    resolve = sub.add_parser("resolve", help="resolve an incident")
    resolve.add_argument("title")

    args = parser.parse_args()
    if args.cmd == "start":
        start_incident(args.title, args.details)
    else:
        resolve_incident(args.title)


if __name__ == "__main__":
    main()
