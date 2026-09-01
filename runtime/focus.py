"""THE FOCUX FOCUS — directed intelligence for ANY agent, aimed ONLY at our real goals.

Any agent (Claude Code, Codex, Cursor, OpenCode...) walking into an attached
project is much more intelligent the moment it reads the focus pack: it knows
OUR real goals, their gaps, the REAL evidence absorbed, where the current work
stands, the survival tier, and the discipline that never bends.

Principles:
- **Goal-directed, not generic**: the pack contains ONLY what serves the
  active objectives. If there are no objectives, it SAYS SO — intelligence
  without goals is noise, and the harness never pretends otherwise.
- **Deterministic assembly, no LLM**: the numbers and state are read from
  memory; nothing is invented for the agent to act on.
- **Delivered three ways**: `focux focus` (console), `.focux/focus.md`
  (file any agent reads at session start), `focux_focus` (MCP tool).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .ingest import recent_signals
from .objectives import objective_status

FOCUS_FILE = "focus.md"


@dataclass(frozen=True)
class FocusPack:
    workspace: str
    objectives: tuple[dict[str, Any], ...] = ()
    signals: tuple[str, ...] = ()
    work: str = ""
    tier: str = ""
    built_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "objectives": list(self.objectives),
            "signals": list(self.signals),
            "work": self.work,
            "tier": self.tier,
            "built_at": self.built_at,
        }


def focus_pack(
    memory,
    workspace: str = "default",
    *,
    tier: str = "",
    cwd: Path | None = None,
) -> FocusPack:
    """Assemble the directed-intelligence pack (deterministic, no LLM)."""
    statuses = objective_status(memory, workspace, tier=tier) if memory else []
    objectives = tuple(
        {
            "objective_id": s.objective.objective_id,
            "title": s.objective.title,
            "kpi": s.objective.kpi,
            "current": s.objective.current,
            "target": s.objective.target,
            "unit": s.objective.unit,
            "progress": round(s.progress, 3),
            "gap": round(s.gap, 3),
            "deadline": s.objective.deadline,
        }
        for s in statuses
    )
    signals = tuple(recent_signals(memory, workspace, per_source=2)) if memory else ()

    work = ""
    from .workflow import load_state, resume_text, status_text, work_root

    root = work_root(cwd)
    if load_state(root) is not None:
        work = status_text(root)

    return FocusPack(
        workspace=workspace,
        objectives=objectives,
        signals=signals,
        work=work,
        tier=tier,
        built_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def format_focus(pack: FocusPack) -> str:
    """Markdown, console-safe (cp1252), honest when there are no goals."""
    lines = ["# THE FOCUX FOCUS - inteligencia dirigida a nuestras metas reales"]
    lines.append(f"workspace: {pack.workspace} | built: {pack.built_at}")
    if pack.tier:
        lines.append(f"survival tier: {pack.tier} (esfuerzo, nunca autorizacion)")
    if pack.objectives:
        lines.append("\n## Metas reales (gaps)")
        for o in pack.objectives:
            lines.append(
                f"- [{o['objective_id']}] {o['title']} | {o['kpi']}: "
                f"{o['current']:.0f}/{o['target']:.0f}"
                f"{(' ' + o['unit']) if o.get('unit') else ''} | "
                f"{o['progress'] * 100:.0f}% | gap {o['gap']:.0f}"
                f" | deadline {o.get('deadline') or 'none'}"
            )
    else:
        lines.append("\n## Metas reales\n(none set - intelligence without goals is "
                     "noise. Set one: `focux objective add '<meta>' --kpi <k> "
                     "--target <n>`, or do the task directly.)")
    if pack.signals:
        lines.append("\n## Evidencia (datos reales absorbidos)")
        lines += [f"- {s}" for s in pack.signals]
    if pack.work:
        lines.append("\n## Estado del trabajo")
        lines.append(pack.work)
    lines.append("\n## Disciplina (nunca se negocia)")
    lines.append("- Money is NEVER auto-approved; REVIEW = human approval.")
    lines.append("- Survival tiers change EFFORT, never authorization.")
    lines.append("- Protected files are never modified; every action is audited.")
    lines.append("- Direct your intelligence ONLY toward the real goals above.")
    return _safe("\n".join(lines))


def focus_dir(cwd: Path | None = None) -> Path:
    """Where the focus file lives: <project>/.focux/."""
    return (cwd or Path.cwd()).resolve() / ".focux"


def write_focus_file(pack: FocusPack, cwd: Path | None = None) -> Path:
    """Refresh .focux/focus.md — the file any agent reads at session start."""
    path = focus_dir(cwd) / FOCUS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_focus(pack), encoding="utf-8")
    return path


def _safe(text: str) -> str:
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")
