"""Tests for the universal agent installer (focux attach) + verifier (doctor)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.attach import (  # noqa: E402
    ALL_AGENTS,
    attach,
    detect_workspace,
    mcp_server_config,
    verify_attached,
)


# --- base files --------------------------------------------------------------

def test_attach_writes_universal_contract(tmp_path: Path) -> None:
    report = attach(tmp_path, REPO)
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents" / "skills" / "focux-brain" / "SKILL.md").exists()
    assert (tmp_path / "constitution.md").exists()
    assert (tmp_path / "memory" / "focux.db").exists()
    assert (tmp_path / ".gitignore").exists()
    assert ".env" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "AGENTS.md" in report.created


def test_attach_is_idempotent(tmp_path: Path) -> None:
    attach(tmp_path, REPO)
    second = attach(tmp_path, REPO)
    assert not second.changed  # nothing created/updated on re-run
    assert "AGENTS.md" in second.skipped


def test_attach_force_refreshes(tmp_path: Path) -> None:
    attach(tmp_path, REPO)
    (tmp_path / "AGENTS.md").write_text("stale content", encoding="utf-8")
    forced = attach(tmp_path, REPO, force=True)
    assert "AGENTS.md" in forced.updated
    assert "THE FOCUX" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


# --- per-agent configs -------------------------------------------------------

def test_attach_claude_mcp_json(tmp_path: Path) -> None:
    attach(tmp_path, REPO, agents=("claude",))
    mcp = json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))
    server = mcp["mcpServers"]["thefocux"]
    assert server["args"][0].endswith("mcp_bridge.py")
    assert server["command"]  # the interpreter


def test_attach_merges_existing_mcp_json(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"other": {"command": "x", "args": ["y"]}}}),
        encoding="utf-8",
    )
    attach(tmp_path, REPO, agents=("claude",))
    servers = json.loads(
        (tmp_path / ".mcp.json").read_text(encoding="utf-8")
    )["mcpServers"]
    assert "other" in servers  # never lost
    assert "thefocux" in servers


def test_attach_codex_toml(tmp_path: Path) -> None:
    attach(tmp_path, REPO, agents=("codex",))
    text = (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers.thefocux]" in text
    assert "mcp_bridge.py" in text


def test_attach_codex_toml_preserves_existing(tmp_path: Path) -> None:
    cfg = tmp_path / ".codex" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('model = "deepseek-v4-flash"\n', encoding="utf-8")
    attach(tmp_path, REPO, agents=("codex",))
    text = cfg.read_text(encoding="utf-8")
    assert 'model = "deepseek-v4-flash"' in text  # preserved
    assert "[mcp_servers.thefocux]" in text  # appended


def test_attach_cursor_copilot_aider(tmp_path: Path) -> None:
    attach(tmp_path, REPO, agents=("cursor", "copilot", "aider"))
    assert (tmp_path / ".cursor" / "rules" / "focux.mdc").exists()
    assert (tmp_path / ".cursor" / "mcp.json").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert "THE FOCUX" in (tmp_path / ".github" / "copilot-instructions.md").read_text(
        encoding="utf-8")
    assert "read: AGENTS.md" in (tmp_path / ".aider.conf.yml").read_text(
        encoding="utf-8")


def test_attach_all_covers_every_agent(tmp_path: Path) -> None:
    report = attach(tmp_path, REPO, agents=("all",))
    created = " ".join(report.created)
    assert "claude .mcp.json" in created
    assert "cursor .cursor/mcp.json" in created
    assert "config.toml" in created  # codex section (label is the path)
    assert ".cursor/rules/focux.mdc" in created
    assert ".aider.conf.yml" in created
    assert ".github/copilot-instructions.md" in created
    assert set(ALL_AGENTS) >= {"claude", "codex", "cursor", "aider",
                               "copilot", "gemini"}


def test_attach_no_mcp_flag(tmp_path: Path) -> None:
    report = attach(tmp_path, REPO, agents=("all",), with_mcp=False)
    assert not (tmp_path / ".mcp.json").exists()
    assert not (tmp_path / ".codex" / "config.toml").exists()
    assert (tmp_path / "AGENTS.md").exists()  # universal contract still there


def test_mcp_server_config_points_at_bridge() -> None:
    cfg = mcp_server_config(REPO)
    assert cfg["args"][0].endswith("mcp_bridge.py")
    assert Path(cfg["args"][0]).exists()


# --- verification (focux doctor --target) ------------------------------------

def test_verify_attached_ok(tmp_path: Path) -> None:
    attach(tmp_path, REPO, agents=("all",))
    rep = verify_attached(tmp_path, REPO)
    assert rep.ok  # all critical checks pass
    labels = [c.label for c in rep.checks]
    assert "AGENTS.md present" in labels
    assert "memory/focux.db opens" in labels
    assert "claude config" in labels  # optional surface reported


def test_verify_attached_detects_missing(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)  # empty workspace
    rep = verify_attached(tmp_path, REPO)
    assert not rep.ok
    missing = [c.label for c in rep.checks if not c.ok and c.critical]
    assert "AGENTS.md present" in missing


def test_verify_detects_stale_agents_md(tmp_path: Path) -> None:
    attach(tmp_path, REPO)
    (tmp_path / "AGENTS.md").write_text("not the focux contract", encoding="utf-8")
    rep = verify_attached(tmp_path, REPO)
    stale = [c for c in rep.checks if c.label == "AGENTS.md is THE FOCUX contract"]
    assert stale and not stale[0].ok
    assert not rep.ok


# --- workspace declaration (memory namespace) --------------------------------

def test_attach_writes_workspace_marker(tmp_path: Path) -> None:
    attach(tmp_path, REPO, workspace_name="mi-negocio")
    marker = tmp_path / ".focux-workspace"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == "mi-negocio"


def test_attach_default_workspace_is_dir_name(tmp_path: Path) -> None:
    target = tmp_path / "mi-negocio"
    attach(target, REPO)
    assert (target / ".focux-workspace").read_text(
        encoding="utf-8").strip() == "mi-negocio"


def test_attach_preserves_existing_workspace(tmp_path: Path) -> None:
    attach(tmp_path, REPO, workspace_name="primero")
    second = attach(tmp_path, REPO)  # no explicit workspace -> preserve
    assert (tmp_path / ".focux-workspace").read_text(
        encoding="utf-8").strip() == "primero"
    assert any("workspace" in s for s in second.skipped)


def test_attach_updates_workspace_with_flag(tmp_path: Path) -> None:
    attach(tmp_path, REPO, workspace_name="primero")
    attach(tmp_path, REPO, workspace_name="segundo")
    assert (tmp_path / ".focux-workspace").read_text(
        encoding="utf-8").strip() == "segundo"


def test_detect_workspace_walks_up(tmp_path: Path) -> None:
    attach(tmp_path, REPO, workspace_name="neg")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert detect_workspace(deep) == "neg"


def test_detect_workspace_default(tmp_path: Path) -> None:
    assert detect_workspace(tmp_path) == "default"


def test_verify_reports_workspace(tmp_path: Path) -> None:
    attach(tmp_path, REPO, workspace_name="neg")
    rep = verify_attached(tmp_path, REPO)
    ws = [c for c in rep.checks if c.label == "workspace declared"]
    assert ws and ws[0].ok and ws[0].detail == "'neg'"
