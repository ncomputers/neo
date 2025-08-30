from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

import api.app.config.validate as validate  # noqa: E402


def _flags_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "feature_flags.yaml"


def test_load_flag_config_parses_types() -> None:
    path = _flags_path()
    original = path.read_text()
    path.write_text("a: true\nb: 'false'\nc: 1\n")
    try:
        flags = validate._load_flag_config()
        assert flags["a"] is True
        assert flags["b"] is False
        assert flags["c"] is True
    finally:
        path.write_text(original)


def test_load_flag_config_invalid_yaml() -> None:
    path = _flags_path()
    original = path.read_text()
    path.write_text("bad: [unclosed")
    try:
        assert validate._load_flag_config() == {}
    finally:
        path.write_text(original)
