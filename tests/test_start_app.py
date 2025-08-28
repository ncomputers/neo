import subprocess
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from start_app import main  # noqa: E402


def test_failed_migration_logs_error(monkeypatch, capsys):
    def fake_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        main()
    err = capsys.readouterr().err
    assert "boom" in err
    assert "database connection failed" in err
