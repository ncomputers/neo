#!/usr/bin/env python3
"""
Create ClickUp Space + Folders + Lists from JSON blueprint.

Prereqs:
  - ClickUp API token (Settings → Apps → API Token)
  - Team ID (a.k.a. Workspace ID). Find via GET /api/v2/team
  - Python 3.8+ and `requests` installed

Usage:
  export CLICKUP_TOKEN="pk_xxx"
  python create_clickup_structure.py --team-id 12345678 --blueprint clickup_structure.json

Notes:
  - Idempotency: The script tries to find existing Space/Folder/List by name before creating.
  - Statuses: Applied at Space level where possible (ClickUp supports custom statuses at Space/Folder).
  - Safe to re-run; it won't duplicate entities with the same name.
"""

import argparse, json, os, sys, time
from typing import Optional, Dict, Any, List
import requests

API_BASE = "https://api.clickup.com/api/v2"

def api_headers():
    token = os.getenv("CLICKUP_TOKEN")
    if not token:
        print("ERROR: CLICKUP_TOKEN env var not set.", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": token, "Content-Type": "application/json"}

def get_teams() -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/team", headers=api_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("teams", [])

def find_team(team_id: Optional[int]) -> Dict[str, Any]:
    teams = get_teams()
    if team_id:
        for t in teams:
            if int(t["id"]) == int(team_id):
                return t
        raise SystemExit(f"Team id {team_id} not found. Available: {[t['id'] for t in teams]}")
    if teams:
        return teams[0]
    raise SystemExit("No teams found for token.")

def get_spaces(team_id: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/team/{team_id}/space", headers=api_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("spaces", [])

def find_or_create_space(team_id: int, space_spec: Dict[str, Any]) -> Dict[str, Any]:
    name = space_spec["name"]
    # Try to find by name
    for s in get_spaces(team_id):
        if s["name"].strip().lower() == name.strip().lower():
            print(f"[=] Space exists: {name} (id={s['id']})")
            return s
    payload = {
        "name": name,
        "color": space_spec.get("color", "#6A5ACD"),
        "multiple_assignees": space_spec.get("multiple_assignees", True),
        "features": {
            "due_dates": {"enabled": space_spec.get("features", {}).get("due_dates", True)},
            "time_tracking": {"enabled": space_spec.get("features", {}).get("time_tracking", False)},
            "tags": {"enabled": space_spec.get("features", {}).get("tags", True)},
        }
    }
    # Create space
    r = requests.post(f"{API_BASE}/team/{team_id}/space", headers=api_headers(), json=payload, timeout=30)
    r.raise_for_status()
    space = r.json()
    print(f"[+] Created Space: {space['name']} (id={space['id']})")

    # Set statuses at space level (ClickUp v2: PUT /space/{space_id} with 'statuses')
    statuses = space_spec.get("statuses")
    if statuses:
        put_payload = {"statuses": statuses}
        rr = requests.put(f"{API_BASE}/space/{space['id']}", headers=api_headers(), json=put_payload, timeout=30)
        if rr.status_code in (200, 204):
            print("[+] Applied custom statuses at space level.")
        else:
            print(f"[!] Could not apply statuses: {rr.status_code} {rr.text}")
    return space

def get_folders(space_id: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/space/{space_id}/folder", headers=api_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("folders", [])

def find_or_create_folder(space_id: int, name: str) -> Dict[str, Any]:
    for f in get_folders(space_id):
        if f["name"].strip().lower() == name.strip().lower():
            print(f"[=] Folder exists: {name} (id={f['id']})")
            return f
    payload = {"name": name}
    r = requests.post(f"{API_BASE}/space/{space_id}/folder", headers=api_headers(), json=payload, timeout=30)
    r.raise_for_status()
    folder = r.json()
    print(f"[+] Created Folder: {name} (id={folder['id']})")
    return folder

def get_lists_in_folder(folder_id: int) -> List[Dict[str, Any]]:
    r = requests.get(f"{API_BASE}/folder/{folder_id}/list", headers=api_headers(), timeout=30)
    r.raise_for_status()
    return r.json().get("lists", [])

def find_or_create_list(folder_id: int, name: str) -> Dict[str, Any]:
    for l in get_lists_in_folder(folder_id):
        if l["name"].strip().lower() == name.strip().lower():
            print(f"[=] List exists: {name} (id={l['id']})")
            return l
    payload = {"name": name}
    r = requests.post(f"{API_BASE}/folder/{folder_id}/list", headers=api_headers(), json=payload, timeout=30)
    r.raise_for_status()
    lst = r.json()
    print(f"[+] Created List: {name} (id={lst['id']})")
    return lst

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team-id", type=int, required=True, help="ClickUp Team/Workspace ID")
    ap.add_argument("--blueprint", type=str, default="clickup_structure.json", help="Blueprint JSON path")
    args = ap.parse_args()

    with open(args.blueprint, "r", encoding="utf-8") as f:
        spec = json.load(f)

    team = find_team(args.team_id)
    print(f"[i] Using team: {team['name']} (id={team['id']})")

    space = find_or_create_space(int(team["id"]), spec["space"])

    # Create folders & lists
    for folder_spec in spec.get("folders", []):
        folder = find_or_create_folder(int(space["id"]), folder_spec["name"])
        for list_name in folder_spec.get("lists", []):
            find_or_create_list(int(folder["id"]), list_name)

    print("[✓] Structure ensured. Done.")

if __name__ == "__main__":
    main()
