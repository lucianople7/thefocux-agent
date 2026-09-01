"""THE FOCUX Work Harness — durable, stage-gated work that outlives sessions.

Mindset adopted from the Automaton harness pattern (MIT, appautomaton):
- Work that spans context windows or needs agreement first goes through
  explicit stages: frame -> plan -> execute -> verify -> verified.
- Anything a single session can finish and verify is done directly — the
  harness SAYS SO at session start instead of leaving you to guess.
- The HUMAN approving SPEC.md at frame's exit is the product review. No
  model gate stands in for product judgment.
- State lives in `.focux/work/` (SPEC.md, PLAN.md, ROADMAP.md, current.json)
  inside the project — durable across sessions, restarts, context resets.
- `verified` is terminal: the harness disengages and later sessions open
  quiet until your next objective. `resume` re-enters existing work.

The FOCUX disciplines stay ON inside the harness: every plan step is gated
by the money-gate before execution, verification runs real checks, and the
constitution is never suspended.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: The stage machine. `verified` is terminal.
STAGES: tuple[str, ...] = ("framed", "planned", "executing", "verifying",
                           "verified")

STATE_FILE = "current.json"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Durable state (.focux/work/)
# ---------------------------------------------------------------------------

@dataclass
class WorkState:
    objective: str
    stage: str
    root: Path
    domain: str = "code"
    created_at: str = ""
    updated_at: str = ""
    history: list[str] = field(default_factory=list)

    @property
    def spec_path(self) -> Path:
        return self.root / "SPEC.md"

    @property
    def plan_path(self) -> Path:
        return self.root / "PLAN.md"

    @property
    def roadmap_path(self) -> Path:
        return self.root / "ROADMAP.md"

    def save(self) -> None:
        self.updated_at = _now()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / STATE_FILE).write_text(
            json.dumps(self.as_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "stage": self.stage,
            "domain": self.domain,
            "root": str(self.root),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "history": self.history,
        }

    def bump(self, stage: str, note: str) -> "WorkState":
        self.stage = stage
        self.history.append(f"{_now()} [{stage}] {note}")
        self.save()
        return self


def work_root(cwd: Path | None = None) -> Path:
    """The harness state dir for the project: <project>/.focux/work/."""
    return (cwd or Path.cwd()).resolve() / ".focux" / "work"


def load_state(root: Path) -> WorkState | None:
    state_file = root / STATE_FILE
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return WorkState(
        objective=str(data.get("objective", "")),
        stage=str(data.get("stage", "framed")),
        root=root,
        domain=str(data.get("domain", "code")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
        history=list(data.get("history", [])),
    )


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def frame(agent, objective: str, *, domain: str = "code",
          workspace: str = "default", cwd: Path | None = None,
          force: bool = False) -> WorkState:
    """frame: write SPEC.md (decision draft) and enter stage `framed`.

    The HUMAN approves the SPEC at frame's exit — that is the product
    review; no model gate stands in for it.
    """
    root = work_root(cwd)
    existing = load_state(root)
    if existing is not None and existing.stage not in ("verified",) and not force:
        raise ValueError(
            f"work already in stage '{existing.stage}' - resume it with "
            "`focux work resume` or force a new frame"
        )
    root.mkdir(parents=True, exist_ok=True)
    now = _now()
    state = WorkState(objective=objective, stage="framed", root=root,
                      domain=domain, created_at=now, updated_at=now,
                      history=[f"{now} [framed] objective framed"])
    spec = _draft_spec(agent, objective, workspace)
    state.spec_path.write_text(spec, encoding="utf-8")
    state.save()
    return state


def _draft_spec(agent, objective: str, workspace: str) -> str:
    """SPEC draft: what, why, success criteria, constraints. Evidence-based."""
    context = _context_lines(agent, workspace)
    prompt = (
        "Write the SPEC for this work. STRICT structure (markdown):\n"
        "# SPEC\n## Objective\n## Why (evidence)\n## Success criteria "
        "(verifiable, numbered)\n## Constraints\n## Out of scope\n"
        "Be concrete and verifiable. Use ONLY the evidence available.\n\n"
        f"OBJECTIVE: {objective}\n\n{context}"
    )
    body = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's work planner. A SPEC is a decision "
        "document the HUMAN will approve: it must make the what, why and "
        "success criteria obvious. Never invent evidence."
    ))
    return f"# WORK SPEC\n\nStatus: DRAFT - awaiting human approval (product review)\n\n{body}\n"


def approve(state: WorkState) -> WorkState:
    """frame's exit: the human approves the SPEC (product review)."""
    if not state.spec_path.exists():
        raise ValueError("no SPEC.md - run `focux work frame` first")
    return state.bump("framed", "SPEC approved by human (product review)")


def plan(agent, state: WorkState, *, workspace: str = "default") -> WorkState:
    """plan: write PLAN.md (gated steps) and enter stage `planned`."""
    context = _context_lines(agent, workspace)
    spec = state.spec_path.read_text(encoding="utf-8") if state.spec_path.exists() else ""
    prompt = (
        "Write the PLAN for this SPEC. STRICT structure (markdown):\n"
        "# PLAN\n## Steps\n1. <action> [pillar: research|content|commerce|monetization|account]\n"
        "2. ...\n## Verification\n- <how this work is proven done>\n\n"
        "Each step MUST declare its pillar so the money-gate can classify it. "
        "Max 6 steps. Concrete and executable.\n\n"
        f"{spec}\n\n{context}"
    )
    body = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's work planner. A PLAN decomposes the SPEC "
        "into gated steps. Each step declares a pillar (research, content, "
        "commerce, monetization, account). Never invent steps without evidence."
    ))
    state.plan_path.write_text(f"# WORK PLAN\n\nStatus: planned\n\n{body}\n",
                               encoding="utf-8")
    return state.bump("planned", "plan written")


def execute(agent, state: WorkState, *, workspace: str = "default") -> list[dict[str, Any]]:
    """execute: gate every plan step BEFORE the work is done.

    The agent (or the human) then does the ALLOW/approved steps across
    sessions. REVIEW steps need human approval first.
    """
    steps = _parse_steps(state.plan_path)
    if not steps:
        raise ValueError("PLAN.md has no parseable steps - run `focux work plan` first")
    gated: list[dict[str, Any]] = []
    for step in steps:
        result = agent.propose(pillar=step["pillar"], objective=step["action"])
        gated.append({**step, "decision": str(result.decision)})
    state.bump("executing", f"{len(gated)} plan steps gated")
    return gated


def verify(agent, state: WorkState, *, workspace: str = "default",
           confirm: bool = False) -> WorkState:
    """verify: run real checks. Pass -> `verified` (terminal, harness off).

    - domain `code`: runs the project's test suite (pytest) when present.
    - domain `content`: the Expert Panel quality review must PASS.
    `confirm` marks verified when no automated check exists (honest: the
    human is the verifier then).
    """
    state.bump("verifying", "verification started")
    checks: list[tuple[str, bool, str]] = []
    if state.domain == "content":
        from .experts import review_draft

        draft = state.spec_path.read_text(encoding="utf-8")
        verdict = review_draft(agent, "content", draft, workspace)
        checks.append(("expert review", verdict.passed, verdict.verdict))
    else:
        # code: run the project's own test suite if a test framework exists
        project_root = state.root.parent.parent  # <project>/.focux/work -> project
        has_pytest = _find_pytest(project_root)
        if has_pytest:
            import subprocess
            import sys

            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                capture_output=True, text=True, timeout=300,
                cwd=str(project_root),
            )
            tail = (proc.stdout or proc.stderr).strip().splitlines()
            checks.append(("pytest", proc.returncode == 0,
                           tail[-1] if tail else f"rc={proc.returncode}"))
        else:
            checks.append(("automated tests", False,
                           "no test framework found in project"))
    passed = all(ok for _, ok, _ in checks)
    if passed:
        state.bump("verified", "verification passed - work closed")
        _write_roadmap(state)
    elif confirm:
        state.bump("verified", "verified by human confirmation (no auto checks)")
        _write_roadmap(state)
    else:
        state.bump("executing", "verification failed - back to executing")
    state.history.append(" | ".join(
        f"{name}={verdict}" for name, ok, verdict in checks
    ))
    state.save()
    return state


def _write_roadmap(state: WorkState) -> None:
    """What comes next after verified (the harness then disengages)."""
    roadmap = (
        "# ROADMAP - next after verified\n\n"
        "The harness is disengaged. Next work: `focux work frame '<objective>'` "
        "or do it directly if it fits one session.\n\n"
        f"Last verified objective: {state.objective}\n"
    )
    state.roadmap_path.write_text(roadmap, encoding="utf-8")


# ---------------------------------------------------------------------------
# Session-start honesty + resume + validate
# ---------------------------------------------------------------------------

def status_text(root: Path) -> str:
    """What the harness says at session start (honest, never guessing)."""
    state = load_state(root)
    if state is None:
        return (
            "No staged work. If today's objective fits one session, DO IT "
            "DIRECTLY (gates still apply). Stage it only if it spans sessions "
            "or needs agreement first: `focux work frame '<objective>'`."
        )
    if state.stage == "verified":
        return (
            f"Quiet: last work verified ('{state.objective}'). The harness is "
            "disengaged. Next objective? Frame it or do it directly."
        )
    if state.stage == "framed":
        return (
            f"SPEC.md awaits YOUR review ({state.spec_path}). Approving it is "
            "the product review - no model gate stands in for you: "
            "`focux work approve` then `focux work plan`."
        )
    if state.stage == "planned":
        return (
            f"Plan ready ({state.plan_path}). Gate it: `focux work execute`. "
            "Then do the ALLOW steps; REVIEW steps need your approval."
        )
    if state.stage == "executing":
        return (
            f"Work in progress ('{state.objective}'). Continue across sessions "
            "with `focux work resume`; close it with `focux work verify`."
        )
    return f"Work in stage '{state.stage}' - `focux work status` for detail."


def resume_text(root: Path) -> str:
    """Re-enter existing work from a fresh session."""
    state = load_state(root)
    if state is None:
        return "Nothing to resume - no .focux/work state in this project."
    lines = [
        f"RESUME (stage: {state.stage})",
        f"  objective: {state.objective}",
        f"  domain: {state.domain}",
    ]
    if state.spec_path.exists():
        lines.append(f"  SPEC: {state.spec_path}")
    if state.plan_path.exists():
        lines.append(f"  PLAN: {state.plan_path}")
    if state.roadmap_path.exists():
        lines.append(f"  ROADMAP: {state.roadmap_path}")
    lines.append("  next: " + {
        "framed": "`focux work approve` (then plan)",
        "planned": "`focux work execute`",
        "executing": "continue the ALLOW steps; `focux work verify` when done",
        "verifying": "`focux work verify` to finish",
        "verified": "done - frame the next objective",
    }.get(state.stage, "`focux work status`"))
    return "\n".join(lines)


def validate(root: Path) -> list[str]:
    """Consistency issues in the work state (like Automaton `validate`)."""
    issues: list[str] = []
    state = load_state(root)
    if state is None:
        return ["no .focux/work state in this project"]
    if not state.spec_path.exists():
        issues.append("SPEC.md missing")
    if state.stage not in STAGES:
        issues.append(f"unknown stage: {state.stage}")
    if state.stage in ("planned", "executing", "verifying", "verified") \
            and not state.plan_path.exists():
        issues.append("PLAN.md missing but stage requires it")
    if state.stage == "verified" and not state.roadmap_path.exists():
        issues.append("ROADMAP.md missing for a verified change")
    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _context_lines(agent, workspace: str) -> str:
    from .ingest import recent_signals

    parts: list[str] = []
    memory = agent.memory
    if memory is not None:
        signals = recent_signals(memory, workspace, per_source=2)
        if signals:
            parts.append("### Absorbed signals (REAL data)")
            parts += [f"- {s}" for s in signals]
    return "\n".join(parts)


def _parse_steps(plan_path: Path) -> list[dict[str, str]]:
    """Parse gated steps from PLAN.md: numbered lines with [pillar: x]."""
    if not plan_path.exists():
        return []
    steps: list[dict[str, str]] = []
    import re

    for line in plan_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = re.match(r"^\d+\.\s+(.+?)\s*\[pillar:\s*([a-z]+)\]$", line, re.I)
        if m:
            steps.append({"action": m.group(1).strip(),
                          "pillar": m.group(2).strip().lower()})
    return steps


def _find_pytest(project_root: Path) -> bool:
    """Is there a test framework to run? (pytest.ini, pyproject, tests/)."""
    candidates = ("pytest.ini", "pyproject.toml", "requirements.txt")
    return any((project_root / c).exists() for c in candidates) or (
        project_root / "tests").is_dir()
