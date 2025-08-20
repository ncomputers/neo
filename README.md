# ClickUp Structure Blueprint

This package creates a ready-to-use **ClickUp Space → Folders → Lists** structure for your QR SaaS project.

## Contents
- `clickup_structure.json` — editable blueprint (Space name, Folders, Lists, statuses)
- `create_clickup_structure.py` — Python script that uses ClickUp API v2 to create the structure
- This README

## What it creates
- **Space**: "QR SaaS" (with custom statuses: To do, In progress, Blocked, In review, Done)
- **Folders**
  - **MVP Epics** → Lists: E1..E17 (one list per epic)
  - **Sprints** → Lists: Sprint 1–4
  - **Operations** → Lists: Onboarding Ops, Support, Bugs, UAT & Releases

> You can rename, add, or remove items in `clickup_structure.json` before running.

## Requirements
- ClickUp API token: Settings → Apps → Copy API Token
- Team (Workspace) ID
  - You can find it via API: `curl -H "Authorization: $CLICKUP_TOKEN" https://api.clickup.com/api/v2/team`
  - Or from the URL when switching Workspaces in the web app.

## How to use
```bash
# 1) Prepare environment
python -m pip install requests

# 2) Set your API token
export CLICKUP_TOKEN="pk_xxx"   # Windows PowerShell: $env:CLICKUP_TOKEN="pk_xxx"

# 3) Edit the blueprint if needed
#    nano clickup_structure.json

# 4) Create the structure
python create_clickup_structure.py --team-id 12345678 --blueprint clickup_structure.json
```

If you rerun the script, it will detect existing Space/Folder/List by name and skip creating duplicates.

## Notes
- Statuses are applied at Space level. You can later override per Folder in ClickUp UI.
- This script **does not** create tasks; import tasks separately using your CSV backlog.
- Safe for dry runs: it only **creates** entities that don't already exist (by name).
- Keep your API token secret.
