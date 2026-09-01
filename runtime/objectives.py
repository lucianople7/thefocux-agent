"""The Objective Brain — real intelligence TOWARD business objectives.

This is the offensive half of THE FOCUX BRAIN. The immune system says NO
(gates); this layer drives the business FORWARD:

- **objective_status()** — deterministic: where each objective stands
  (current vs target vs deadline), the gap, the momentum (delta since the
  last measurement), and the survival tier that should shape effort.
- **drive()** — the intelligence pass: gathers the objectives, their gaps,
  the REAL absorbed signals and the tier, then asks the LLM (any provider)
  for concrete, evidence-based next actions, ONE PER ACTIVE OBJECTIVE. Every
  proposed action is classified by pillar and passed through the money-gate
  BEFORE it becomes part of the plan — so the brain proposes with
  intelligence but never auto-authorizes. REVIEW actions are human-gated.

Discipline: the LLM proposes, the gate decides, the human approves REVIEW,
the operator measures (``focux objective set <id> --current N``), and the
brain adjusts. Momentum = measured progress rising, never vibes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from .memory import Objective


# ---------------------------------------------------------------------------
# Status (deterministic — no LLM in the numbers)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjectiveStatus:
    objective: Objective
    progress: float  # 0..1
    gap: float  # target - current (positive = work remains)
    overdue: bool
    achieved: bool
    delta: float  # current - previous measured value (momentum)
    tier: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective.objective_id,
            "title": self.objective.title,
            "kpi": self.objective.kpi,
            "current": self.objective.current,
            "target": self.objective.target,
            "unit": self.objective.unit,
            "deadline": self.objective.deadline,
            "progress": round(self.progress, 3),
            "gap": round(self.gap, 3),
            "overdue": self.overdue,
            "achieved": self.achieved,
            "delta": round(self.delta, 3),
            "tier": self.tier,
        }


def objective_status(
    memory, workspace: str, *, now: datetime | None = None,
    tier: str = "",
) -> list[ObjectiveStatus]:
    """Where each objective stands: progress, gap, overdue, momentum."""
    now = now or datetime.now(UTC)
    statuses: list[ObjectiveStatus] = []
    for obj in memory.objectives(workspace):
        history = memory.objective_history(obj.objective_id)
        previous = history[-2][1] if len(history) >= 2 else obj.current
        delta = obj.current - previous
        overdue = bool(obj.deadline) and (
            date.fromisoformat(obj.deadline) < now.date()
        ) and obj.progress() < 1.0
        statuses.append(ObjectiveStatus(
            objective=obj,
            progress=obj.progress(),
            gap=max(0.0, obj.target - obj.current),
            overdue=overdue,
            achieved=obj.progress() >= 1.0,
            delta=delta,
            tier=tier,
        ))
    return statuses


# ---------------------------------------------------------------------------
# Drive: the intelligence pass (LLM proposes, gate decides)
# ---------------------------------------------------------------------------

@dataclass
class DriveReport:
    workspace: str
    statuses: list[ObjectiveStatus] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "statuses": [s.as_dict() for s in self.statuses],
            "actions": self.actions,
            "note": self.note,
        }


_DRIVE_SYSTEM = (
    "You are THE FOCUX BRAIN, the strategic intelligence of a business. "
    "Your job: move the business TOWARD its objectives using REAL evidence. "
    "Never invent data you cannot see; if evidence is thin, say so and propose "
    "the smallest verification step. Proposals must be concrete and mapped to "
    "a pillar: research (analysis), content (create), commerce (sell), "
    "monetization (charge money), account (credentials/config)."
)

_DRIVE_PROMPT = """Business objectives (workspace: {workspace}):

{objectives}

Survival tier (effort guidance, never authorization): {tier}

For EACH active objective, propose exactly ONE concrete next action that best
moves current toward target given the gaps and evidence above. Be specific
and evidence-based. If the objective is achieved, propose the next escalation
or skip it.

Answer STRICTLY as a JSON array, no markdown, no extra text:
[
  {{
    "objective_id": "<id>",
    "action": "one concrete sentence",
    "pillar": "research|content|commerce|monetization|account",
    "amount": 0,
    "target": ""
  }}
]"""


def _parse_plan(text: str) -> list[dict[str, Any]]:
    """Tolerant JSON-array extraction from LLM output (fences, prose)."""
    if not text:
        return []
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        # fall back to one-object-per-line JSON
        data = []
        for line in text[start : end + 1].splitlines():
            line = line.strip().rstrip(",")
            if line.startswith("{"):
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not isinstance(data, list):
        return []
    clean: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "")).strip()
        if not action:
            continue
        clean.append({
            "objective_id": str(item.get("objective_id", "")).strip(),
            "action": action[:200],
            "pillar": str(item.get("pillar", "research")).strip().lower(),
            "amount": float(item.get("amount", 0) or 0),
            "target": str(item.get("target", "") or ""),
        })
    return clean


def drive(
    agent,
    workspace: str,
    *,
    objective_id: str = "",
    limit: int = 3,
    tier: str = "normal",
) -> DriveReport:
    """The intelligence pass: gap analysis -> gated action plan.

    Every proposed action goes through the money-gate BEFORE it enters the
    plan, so the brain proposes freely but NEVER auto-authorizes money,
    publishing or account changes.
    """
    report = DriveReport(workspace=workspace)
    memory = agent.memory
    if memory is None:
        report.note = "no memory attached - the brain needs its SQLite store"
        return report

    statuses = objective_status(memory, workspace, tier=tier)
    if objective_id:
        statuses = [s for s in statuses
                    if s.objective.objective_id == objective_id]
    if not statuses:
        report.note = "no objectives - add one: focux objective add '<title>' --kpi <kpi> --target <n>"
        return report
    report.statuses = statuses

    # evidence pack: facts + procedures (the intelligence input). REAL signals
    # are auto-injected by agent.draft() as "## Absorbed signals (REAL data)".
    facts = [f.as_dict() for f in memory.facts(workspace)[:8]]
    procedures = [p.as_dict() for p in memory.procedures(workspace)[:5]]

    objectives_txt = "\n".join(
        f"- [{s.objective.objective_id}] {s.objective.title} | "
        f"{s.objective.kpi}: {s.objective.current:.0f}/{s.objective.target:.0f}"
        f"{(' ' + s.objective.unit) if s.objective.unit else ''} | "
        f"progress {s.progress * 100:.0f}% | deadline {s.objective.deadline or 'none'}"
        for s in statuses[: limit * 2]
    )
    evidence_txt = "\n".join(
        ["### Business facts"] + [f"- {f['key']}: {f['value']}" for f in facts]
        + ["### Procedures (what has been tried)"] + [f"- {p['name']} (ok={p['success_count']}, fail={p['fail_count']})" for p in procedures]
    )

    prompt = _DRIVE_PROMPT.format(
        workspace=workspace, objectives=objectives_txt, tier=tier
    ) + "\n\n" + evidence_txt

    # real intelligence: the LLM (any provider) reasons with the evidence
    text = agent.draft(prompt, system=_DRIVE_SYSTEM)
    proposals = _parse_plan(text)[:limit]
    if not proposals:
        report.note = ("the brain could not parse a plan from the model "
                       "(honest: no invented plan)")
        return report

    # the gate decides BEFORE anything becomes a plan
    for prop in proposals:
        result = agent.propose(
            pillar=prop["pillar"],
            objective=prop["action"],
            amount=prop["amount"],
            target=prop["target"],
        )
        report.actions.append({
            **prop,
            "decision": str(result.decision),
            "summary": result.summary,
        })
    # store the gated plan on each touched objective
    by_id: dict[str, list[dict[str, Any]]] = {}
    for a in report.actions:
        by_id.setdefault(a["objective_id"], []).append(a)
    for oid, actions in by_id.items():
        memory.set_objective_plan(workspace, oid, actions)
    return report


# ---------------------------------------------------------------------------
# Formatting (console-safe: Windows cp1252)
# ---------------------------------------------------------------------------

def _safe(text: str) -> str:
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")


def format_status(statuses: list[ObjectiveStatus]) -> str:
    lines = ["OBJECTIVES (workspace status):"]
    for s in statuses:
        mark = "ACHIEVED" if s.achieved else ("OVERDUE" if s.overdue else "active")
        delta = f" | delta {s.delta:+.0f}" if s.delta else ""
        lines.append(
            f"  [{mark:8s}] {s.objective.title} | {s.objective.kpi}: "
            f"{s.objective.current:.0f}/{s.objective.target:.0f}"
            f"{(' ' + s.objective.unit) if s.objective.unit else ''} | "
            f"{s.progress * 100:.0f}%{delta}"
            f" | deadline {s.objective.deadline or 'none'}"
        )
    if not statuses:
        lines.append("  (no objectives yet - add one with focux objective add)")
    return _safe("\n".join(lines))


def format_drive(report: DriveReport) -> str:
    lines = [f"DRIVE (workspace: {report.workspace})"]
    for s in report.statuses:
        lines.append(
            f"  [{s.objective.objective_id}] {s.objective.title} | "
            f"gap {s.gap:.0f} {s.objective.unit} | tier {s.tier}"
        )
    if not report.actions:
        lines.append(f"  note: {report.note}")
        return _safe("\n".join(lines))
    lines.append("  proposed plan (gated BEFORE entering the plan):")
    for a in report.actions:
        lines.append(
            f"    [{a['decision']}] ({a['pillar']}) {a['action']}"
            + (f" | amount {a['amount']:.0f}" if a.get("amount") else "")
        )
    reviews = [a for a in report.actions if a["decision"] == "REVIEW"]
    if reviews:
        lines.append("  REVIEW actions need human approval before execution.")
    return _safe("\n".join(lines))
