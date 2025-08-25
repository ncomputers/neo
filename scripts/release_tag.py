#!/usr/bin/env python3
"""Tag a release and update the changelog.

This helper scans merged pull requests since the last git tag,
collects their titles and labels from the GitHub API and groups
entries by ``feat``, ``fix``, ``chore`` and ``docs``. A new entry is
prepended to ``CHANGELOG.md`` and a git tag is created and pushed.

The script assumes ``GITHUB_TOKEN`` is available in the environment so
API requests and pushes are authenticated.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

BASE_VERSION = "v1.0.0"


def _run(cmd: List[str]) -> str:
    """Run a command and return its output."""

    return subprocess.check_output(cmd, text=True).strip()


def get_repo() -> Tuple[str, str]:
    """Return ``(owner, repo)`` from the configured origin."""

    url = _run(["git", "config", "--get", "remote.origin.url"])
    url = url.removesuffix(".git")
    if url.startswith("git@"):
        path = url.split(":", 1)[1]
    elif url.startswith("https://github.com/"):
        path = url.split("github.com/", 1)[1]
    else:
        raise RuntimeError(f"Unsupported remote url: {url}")
    owner, repo = path.split("/", 1)
    return owner, repo


def last_tag() -> str | None:
    try:
        return _run(["git", "describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def merged_pr_numbers(since: str | None) -> List[int]:
    rev = f"{since}..HEAD" if since else "HEAD"
    log = _run(["git", "log", "--merges", "--pretty=%s", rev])
    numbers = set()
    for line in log.splitlines():
        match = re.search(r"#(\d+)", line)
        if match:
            numbers.add(int(match.group(1)))
    return sorted(numbers)


def fetch_pr(pr: int, owner: str, repo: str) -> Tuple[str, List[str]]:
    """Return ``(title, labels)`` for ``pr``."""

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    labels = [lbl["name"].lower() for lbl in data.get("labels", [])]
    return data["title"], labels


def build_groups(prs: Dict[int, Tuple[str, List[str]]]) -> str:
    groups: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for num, (title, labels) in prs.items():
        group = "other"
        for candidate in ["feat", "fix", "chore", "docs"]:
            if candidate in labels:
                group = candidate
                break
        groups[group].append((num, title))

    order = ["feat", "fix", "chore", "docs", "other"]
    lines: List[str] = []
    for key in order:
        items = groups.get(key)
        if not items:
            continue
        lines.append(f"### {key.title()}\n")
        for num, title in items:
            lines.append(f"- {title} (#{num})\n")
        lines.append("\n")
    return "".join(lines).rstrip() + "\n"


def next_tag(current: str | None, final: bool) -> str:
    if final:
        return BASE_VERSION
    if current and current.startswith(f"{BASE_VERSION}-rc"):
        try:
            n = int(current.split("-rc")[1])
        except ValueError:
            n = 0
    else:
        n = 0
    return f"{BASE_VERSION}-rc{n + 1}"


def update_changelog(tag: str, body: str) -> None:
    path = Path("CHANGELOG.md")
    existing = path.read_text() if path.exists() else "# Changelog\n\n"
    date = _dt.date.today().isoformat()
    entry = f"## {tag} - {date}\n\n{body}\n"
    path.write_text(existing + entry)


def create_tag(tag: str) -> None:
    _run(["git", "tag", tag])
    _run(["git", "push", "origin", tag])


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tag a release")
    parser.add_argument("--final", action="store_true", help="create final release tag")
    args = parser.parse_args(list(argv) if argv is not None else None)

    owner, repo = get_repo()
    last = last_tag()
    pr_numbers = merged_pr_numbers(last)
    prs = {num: fetch_pr(num, owner, repo) for num in pr_numbers}

    body = build_groups(prs)
    tag = next_tag(last, args.final)

    update_changelog(tag, body)
    create_tag(tag)
    return 0


if __name__ == "__main__":  # pragma: no cover - script entry
    raise SystemExit(main())
