"""Tests for the global CLI installer (`focux install`)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.install import (  # noqa: E402
    default_prefix,
    install_launchers,
    register_user_mcp,
)


def test_install_launchers_written(tmp_path: Path) -> None:
    created = install_launchers(tmp_path, REPO)
    launcher = tmp_path / "focux"
    cmd = tmp_path / "focux.cmd"
    assert launcher.exists()
    assert cmd.exists()
    web = tmp_path / "focux-web"
    assert web.exists()
    assert str(REPO.resolve()) in launcher.read_text(encoding="utf-8")
    assert len(created) == 4  # focux + focux.cmd + focux-web + focux-web.cmd


def test_launcher_answers_help(tmp_path: Path) -> None:
    install_launchers(tmp_path, REPO)
    proc = subprocess.run(
        [sys.executable, str(tmp_path / "focux"), "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "usage" in proc.stdout
    assert "attach" in proc.stdout
    assert "install" in proc.stdout  # the new subcommand is wired


def test_web_launcher_wired(tmp_path: Path) -> None:
    install_launchers(tmp_path, REPO)
    text = (tmp_path / "focux-web").read_text(encoding="utf-8")
    assert "from webui import main" in text


def test_default_prefix_in_home() -> None:
    prefix = default_prefix()
    assert prefix.name == "bin"
    assert ".thefocux" in prefix.parts


def test_register_user_mcp_codex(tmp_path: Path) -> None:
    cfg = tmp_path / "codex.toml"
    cfg.write_text('model = "deepseek-v4-flash"\n', encoding="utf-8")
    report = register_user_mcp(REPO, codex_config=cfg)
    text = cfg.read_text(encoding="utf-8")
    assert 'model = "deepseek-v4-flash"' in text  # preserved
    assert "[mcp_servers.thefocux]" in text  # appended
    assert "mcp_bridge.py" in text
    assert any("claude mcp add" in n for n in report.notes)


def test_register_user_mcp_idempotent(tmp_path: Path) -> None:
    cfg = tmp_path / "codex.toml"
    register_user_mcp(REPO, codex_config=cfg)
    second = register_user_mcp(REPO, codex_config=cfg)
    assert second.skipped  # section already present -> skipped, not duplicated
    assert cfg.read_text(encoding="utf-8").count(
        "[mcp_servers.thefocux]") == 1
