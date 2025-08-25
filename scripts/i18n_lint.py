#!/usr/bin/env python3
# i18n_lint.py
"""Ensure translation files share the same keys across languages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Set


def collect_keys(tree: dict, prefix: str = "") -> Set[str]:
    """Recursively gather dotted paths for all keys in *tree*."""
    keys: Set[str] = set()
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        keys.add(path)
        if isinstance(value, dict):
            keys |= collect_keys(value, path)
    return keys


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    i18n_dir = repo_root / "api" / "app" / "i18n"
    langs = ["en", "hi", "gu"]
    key_sets: Dict[str, Set[str]] = {}

    for lang in langs:
        with open(i18n_dir / f"{lang}.json", "r", encoding="utf-8") as fh:
            data = json.load(fh)
        key_sets[lang] = collect_keys(data)

    all_keys = set().union(*key_sets.values())
    missing = {lang: sorted(all_keys - keys) for lang, keys in key_sets.items() if all_keys - keys}

    if missing:
        for lang, keys in missing.items():
            print(f"{lang} missing keys: {', '.join(keys)}")
        return 1

    print("All translation keys present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
