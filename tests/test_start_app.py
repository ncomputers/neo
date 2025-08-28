import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from start_app import main  # noqa: E402


def test_failed_migration_surfaces_output(monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            2, cmd, output="out\n", stderr="err\n"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as excinfo:
        main()

    captured = capsys.readouterr()
    assert "out" in captured.out
    assert "err" in captured.err
    assert "exit code 2" in captured.err
    assert excinfo.value.code == 2
