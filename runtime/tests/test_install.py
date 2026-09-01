"""Tests for the global CLI installer (`focux install`)."""
from __future__ import annotations

import json
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
    uninstall,
    user_mcp_registered,
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
    report = register_user_mcp(
        REPO, codex_config=cfg,
        claude_config=tmp_path / "claude.json",
        cursor_config=tmp_path / "cursor.json",
    )
    text = cfg.read_text(encoding="utf-8")
    assert 'model = "deepseek-v4-flash"' in text  # preserved
    assert "[mcp_servers.thefocux]" in text  # appended
    assert "mcp_bridge.py" in text
    assert any("Restart" in n for n in report.notes)


def test_register_user_mcp_idempotent(tmp_path: Path) -> None:
    cfg = tmp_path / "codex.toml"
    claude = tmp_path / "claude.json"
    cursor = tmp_path / "cursor.json"
    kwargs = dict(codex_config=cfg, claude_config=claude, cursor_config=cursor)
    register_user_mcp(REPO, **kwargs)
    second = register_user_mcp(REPO, **kwargs)
    assert second.skipped  # already present -> skipped, not duplicated
    assert cfg.read_text(encoding="utf-8").count(
        "[mcp_servers.thefocux]") == 1
    assert json.loads(claude.read_text(encoding="utf-8"))["mcpServers"][
        "thefocux"]["args"][0].endswith("mcp_bridge.py")


def test_register_user_mcp_claude_preserves(tmp_path: Path) -> None:
    """~/.claude.json is huge and user-owned: merge must never lose keys."""
    claude = tmp_path / "claude.json"
    claude.write_text(json.dumps({
        "projects": {"c:\\work\\x": {"history": [1, 2, 3]}},
        "mcpServers": {"other": {"command": "npx", "args": ["-y", "other"]}},
        "theme": "dark",
    }), encoding="utf-8")
    register_user_mcp(
        REPO, codex_config=tmp_path / "codex.toml",
        claude_config=claude, cursor_config=tmp_path / "cursor.json",
    )
    data = json.loads(claude.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"  # untouched
    assert data["projects"]["c:\\work\\x"]["history"] == [1, 2, 3]  # untouched
    servers = data["mcpServers"]
    assert "other" in servers  # other MCP servers kept
    assert servers["thefocux"]["args"][0].endswith("mcp_bridge.py")


def test_register_user_mcp_cursor(tmp_path: Path) -> None:
    cursor = tmp_path / "cursor.json"
    register_user_mcp(
        REPO, codex_config=tmp_path / "codex.toml",
        claude_config=tmp_path / "claude.json", cursor_config=cursor,
    )
    data = json.loads(cursor.read_text(encoding="utf-8"))
    assert data["mcpServers"]["thefocux"]["args"][0].endswith("mcp_bridge.py")


def test_user_mcp_registered_probe(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    (home / ".codex" / "config.toml").write_text(
        "[mcp_servers.thefocux]\n", encoding="utf-8")
    (home / ".cursor").mkdir(parents=True)
    (home / ".cursor" / "mcp.json").write_text(
        '{"mcpServers": {"thefocux": {}}}', encoding="utf-8")
    status = user_mcp_registered(home)
    assert status == {"codex": True, "claude": False, "cursor": True}


def test_uninstall_removes_surface_preserves_history(tmp_path: Path) -> None:
    """Automaton rule: uninstall removes launchers + MCP, keeps .focux."""
    prefix = tmp_path / "bin"
    install_launchers(prefix, REPO)
    assert (prefix / "focux").exists()

    # simulate durable history that must survive
    history = tmp_path / ".focux" / "work"
    history.mkdir(parents=True)
    (history / "SPEC.md").write_text("# durable", encoding="utf-8")

    cfg = tmp_path / "codex.toml"
    claude = tmp_path / "claude.json"
    cursor = tmp_path / "cursor.json"
    kwargs = dict(codex_config=cfg, claude_config=claude, cursor_config=cursor)
    register_user_mcp(REPO, **kwargs)
    assert "[mcp_servers.thefocux]" in cfg.read_text(encoding="utf-8")

    report = uninstall(prefix, REPO, **kwargs)
    assert not (prefix / "focux").exists()
    assert not (prefix / "focux.cmd").exists()
    assert "[mcp_servers.thefocux]" not in cfg.read_text(encoding="utf-8")
    assert "thefocux" not in json.loads(claude.read_text(encoding="utf-8"))[
        "mcpServers"]
    assert (history / "SPEC.md").exists()  # history preserved
    assert any("preserved" in n for n in report.notes)
