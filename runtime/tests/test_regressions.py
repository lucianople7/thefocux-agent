"""Regression tests from the rigorous probe rounds (not lazy passes).

Round 1: selfmod must never crash on non-serializable audit data.
Round 4: CLI errors must be clean messages, never tracebacks.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def test_cli_promote_missing_is_clean(tmp_path: Path) -> None:
    """REGRESSION round 4: no traceback for missing draft."""
    proc = subprocess.run(
        [sys.executable, "-m", "focux", "promote", "missing-skill"],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert proc.returncode == 2
    assert "Traceback" not in proc.stdout + proc.stderr
    assert "no draft skill" in (proc.stdout + proc.stderr)


def test_cli_unknown_command_is_clean() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "focux", "does-not-exist"],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert proc.returncode == 2
    assert "Traceback" not in proc.stdout + proc.stderr
