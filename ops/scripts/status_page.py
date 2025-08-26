import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

STATUS_FILE = Path(__file__).resolve().parents[2] / "status.json"


def _read_status() -> Dict[str, Any]:
    with STATUS_FILE.open() as f:
        return json.load(f)


def _write_status(data: Dict[str, Any]) -> None:
    with STATUS_FILE.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def start_incident(title: str, details: str) -> None:
    data = _read_status()
    data["state"] = "degraded"
    incidents = data.setdefault("incidents", [])
    incidents.append(
        {
            "title": title,
            "details": details,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    _write_status(data)


def resolve_incident(title: str) -> None:
    data = _read_status()
    incidents = [i for i in data.get("incidents", []) if i.get("title") != title]
    data["incidents"] = incidents
    data["state"] = "degraded" if incidents else "operational"
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
