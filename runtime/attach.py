"""Universal agent attach: mount THE FOCUX BRAIN into ANY coding agent's workspace.

`focux attach <dir>` writes the universal contract (AGENTS.md, brain skill,
constitution, shared SQLite memory) plus per-agent configs so Claude Code,
OpenAI Codex, Cursor, Aider, GitHub Copilot and Gemini CLI all pick up the
brain with ZERO manual setup.

Rules of the installer:
- Idempotent: re-running never duplicates or clobbers user files.
- Non-destructive: existing JSON is MERGED (servers kept), existing TOML is
  APPENDED (other sections kept), invalid files are left untouched with a note.
- `--force` refreshes the files THE FOCUX owns (AGENTS.md, brain skill,
  constitution, .gitignore) but still merges user-owned configs safely.

Verification: `verify_attached()` checks a workspace end-to-end and is what
`focux doctor --target <dir>` reports.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: Agent id -> human-readable label (the config surface each one gets).
AGENTS: dict[str, str] = {
    "claude": "Claude Code (.mcp.json + AGENTS.md)",
    "codex": "OpenAI Codex (.codex/config.toml MCP + AGENTS.md)",
    "cursor": "Cursor (.cursor/mcp.json + rules/focux.mdc)",
    "aider": "Aider (.aider.conf.yml auto-reads AGENTS.md)",
    "copilot": "GitHub Copilot (.github/copilot-instructions.md)",
    "gemini": "Gemini CLI (AGENTS.md natively; no extra file)",
}

ALL_AGENTS: tuple[str, ...] = tuple(AGENTS)

_MEM_README = (
    "FOCUX BRAIN shared memory: metrics.md, decisions.md, receipts/, "
    "focux.db (SQLite), selfmod.jsonl (audit)."
)

_GITIGNORE = ".env\nmemory/focux.db\nmemory/focux.db-*\nmemory/selfmod.jsonl\n"

_CURSOR_RULE = """---
description: THE FOCUX BRAIN - business discipline for every change. Apply always.
globs: "**/*"
alwaysApply: true
---
You are THE FOCUX BRAIN attached to this business. Read `AGENTS.md` and
`.agents/skills/focux-brain/SKILL.md` first. Operate the loop ANALIZAR ->
PLANIFICAR -> EJECUTAR -> MEDIR -> MEJORAR. Money is never auto-approved;
survival tiers change effort, never authorization; every change is audited.
"""

_COPILOT_INSTR = """# THE FOCUX BRAIN

You are THE FOCUX BRAIN attached to this repository. Read AGENTS.md and
.agents/skills/focux-brain/SKILL.md before answering. Operate the business
loop ANALIZAR -> PLANIFICAR -> EJECUTAR -> MEDIR -> MEJORAR with the
constitution as the highest law. Money is never auto-approved; approvals are
single-use and expiring; every executed action writes a receipt.
"""


def _python() -> str:
    """The interpreter that runs the MCP bridge (absolute, robust)."""
    return sys.executable or "python"


def mcp_server_config(repo_root: Path) -> dict:
    """The thefocux-dna MCP server entry (stdio JSON-RPC, zero deps)."""
    return {
        "command": _python(),
        "args": [str((repo_root / "mcp_bridge.py").resolve())],
    }


@dataclass
class AttachReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.created or self.updated)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "notes": self.notes,
        }


def attach(
    workspace: Path,
    repo_root: Path,
    *,
    agents: tuple[str, ...] = ("all",),
    force: bool = False,
    with_mcp: bool = True,
) -> AttachReport:
    """Mount THE FOCUX BRAIN on ``workspace`` for the requested agents."""
    report = AttachReport()
    ws = workspace.resolve()
    ws.mkdir(parents=True, exist_ok=True)

    def write(dst: Path, content: str, label: str) -> None:
        """Write a file THE FOCUX owns; skip existing unless --force."""
        if dst.exists() and not force:
            report.skipped.append(label)
            return
        existed = dst.exists()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
        (report.updated if existed else report.created).append(label)

    # --- universal contract (read by EVERY agent) ---------------------------
    write(ws / "AGENTS.md",
          (repo_root / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md")
    write(ws / ".agents" / "skills" / "focux-brain" / "SKILL.md",
          (repo_root / "skills" / "focux-brain" / "SKILL.md").read_text(
              encoding="utf-8"),
          ".agents/skills/focux-brain/SKILL.md")
    write(ws / "constitution.md",
          (repo_root / "constitution.md").read_text(encoding="utf-8"),
          "constitution.md")

    # --- shared business memory ---------------------------------------------
    mem_dir = ws / "memory"
    mem_readme = mem_dir / "README.md"
    if mem_readme.exists() and not force:
        report.skipped.append("memory/")
    else:
        existed = mem_readme.exists()
        mem_dir.mkdir(parents=True, exist_ok=True)
        mem_readme.write_text(_MEM_README, encoding="utf-8")
        (report.updated if existed else report.created).append("memory/")

    db = mem_dir / "focux.db"
    if not db.exists():
        try:
            from .memory import FocuxMemory

            FocuxMemory(db)
            report.created.append("memory/focux.db (SQLite initialized)")
        except Exception as exc:  # noqa: BLE001 - non-fatal
            report.notes.append(f"memory db init skipped: {exc}")

    # --- hygiene: secrets never committed -----------------------------------
    env_src = repo_root / ".env.example"
    if env_src.exists():
        write(ws / ".env",
              env_src.read_text(encoding="utf-8"),
              ".env (from example - add your API key)")
    write(ws / ".gitignore", _GITIGNORE,
          ".gitignore (secrets + memory ignored)")

    # --- per-agent surfaces ---------------------------------------------------
    want = set(a.strip().lower() for a in agents if a.strip())
    if "all" in want:
        want = set(ALL_AGENTS)

    if with_mcp:
        server = mcp_server_config(repo_root)
        if "claude" in want:
            _merge_mcp_json(ws / ".mcp.json", server, report,
                            "claude .mcp.json", force=force)
        if "cursor" in want:
            _merge_mcp_json(ws / ".cursor" / "mcp.json", server, report,
                            "cursor .cursor/mcp.json", force=force)
        if "codex" in want:
            _append_codex_toml(ws / ".codex" / "config.toml", server, report)
    if "cursor" in want:
        write(ws / ".cursor" / "rules" / "focux.mdc", _CURSOR_RULE,
              ".cursor/rules/focux.mdc")
    if "aider" in want:
        write(ws / ".aider.conf.yml", "read: AGENTS.md\n", ".aider.conf.yml")
    if "copilot" in want:
        write(ws / ".github" / "copilot-instructions.md", _COPILOT_INSTR,
              ".github/copilot-instructions.md")
    if "gemini" in want:
        report.notes.append(
            "gemini: Gemini CLI reads AGENTS.md natively - no extra file needed"
        )
    return report


def _merge_mcp_json(
    path: Path, server: dict, report: AttachReport, label: str,
    *, force: bool = False,
) -> None:
    """Merge thefocux into an existing .mcp.json (never loses other servers)."""
    existed = path.exists()
    if existed:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.notes.append(
                f"{label}: existing file is invalid JSON ({exc}); left untouched"
            )
            return
        servers = payload.setdefault("mcpServers", {})
        if "thefocux" in servers and not force:
            report.skipped.append(label)
            return
        servers["thefocux"] = server
    else:
        payload = {"mcpServers": {"thefocux": server}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (report.updated if existed else report.created).append(label)


def _append_codex_toml(
    path: Path, server: dict, report: AttachReport
) -> None:
    """Append the MCP section to Codex config (preserves other sections)."""
    bridge = server["args"][0].replace("\\", "/")  # TOML-safe path
    block = (
        "\n[mcp_servers.thefocux]\n"
        f'command = "{server["command"]}"\n'
        f'args = ["{bridge}"]\n'
    )
    existed = path.exists()
    if existed:
        text = path.read_text(encoding="utf-8")
        if "[mcp_servers.thefocux]" in text:
            report.skipped.append("codex .codex/config.toml (section present)")
            return
        path.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
        report.updated.append("codex .codex/config.toml (MCP section merged)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block.lstrip("\n"), encoding="utf-8")
        report.created.append("codex .codex/config.toml")


# ---------------------------------------------------------------------------
# Verification (`focux doctor --target <dir>`)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str = ""
    critical: bool = True


@dataclass
class VerifyReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks if c.critical)

    def add(self, label: str, cond: bool, detail: str = "",
            critical: bool = True) -> None:
        self.checks.append(Check(label, bool(cond), detail, critical))


def verify_attached(workspace: Path, repo_root: Path) -> VerifyReport:
    """Check an attached workspace end-to-end (critical + optional surfaces)."""
    ws = workspace.resolve()
    rep = VerifyReport()

    agents_md = ws / "AGENTS.md"
    rep.add("AGENTS.md present", agents_md.exists())
    if agents_md.exists():
        rep.add("AGENTS.md is THE FOCUX contract",
                "THE FOCUX" in agents_md.read_text(encoding="utf-8"))

    skill = ws / ".agents" / "skills" / "focux-brain" / "SKILL.md"
    rep.add("focux-brain skill present", skill.exists())
    if skill.exists():
        rep.add("brain skill valid (name: focux-brain)",
                "name: focux-brain" in skill.read_text(encoding="utf-8"))

    rep.add("constitution present", (ws / "constitution.md").exists())

    gitignore = ws / ".gitignore"
    rep.add(".gitignore ignores secrets",
            gitignore.exists() and ".env" in gitignore.read_text(
                encoding="utf-8"))

    db = ws / "memory" / "focux.db"
    if db.exists():
        try:
            from .memory import FocuxMemory

            mem = FocuxMemory(db)
            mem.close()
            rep.add("memory/focux.db opens", True, "SQLite ok")
        except Exception as exc:  # noqa: BLE001
            rep.add("memory/focux.db opens", False,
                    f"{type(exc).__name__}: {exc}")
    else:
        rep.add("memory/focux.db", False,
                "missing - run 'focux attach'")

    # Optional per-agent surfaces: enhancement, never critical.
    probes = (
        ("claude config", ws / ".mcp.json"),
        ("cursor config", ws / ".cursor" / "mcp.json"),
        ("codex config", ws / ".codex" / "config.toml"),
        ("aider config", ws / ".aider.conf.yml"),
        ("copilot config", ws / ".github" / "copilot-instructions.md"),
    )
    for label, probe in probes:
        rep.add(label, probe.exists(), critical=False)
    return rep
