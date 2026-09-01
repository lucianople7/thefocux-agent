"""THE FOCUX IMPROVE — the success governor: better at all hours.

The metaskill's core discipline: the brain rules the project toward success
through CONTINUOUS improvement, not just daily cycles. `focux improve` can
run at any hour - after a verified change, at session end, before a plan,
inside the daily ritual.

Evidence in, proposals out (gated):
- Real goals + gaps (focus), survival tier
- Lessons accumulated (work memory)
- Procedures that FAILED (what to fix)
- Contract drift (what to re-sync)
- Momentum (what is working)

The LLM proposes concrete improvements (target: business OR system - the
brain improves itself too), each with a before/after metric and a pillar.
Every proposal passes the money-gate BEFORE it enters the plan, and is
stored as an `improve` event so the next cycle sees what was proposed.
Nothing auto-applies: propose -> human approves -> work harness stages it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_IMPROVE_PROMPT = """You are THE FOCUX BRAIN's success governor. The rule:
improvements at all hours, always measured. Given the evidence below, propose
exactly {limit} concrete improvements that move the business toward its real
goals OR make THE FOCUX itself better. Each must have a verifiable
before->after metric.

Reply STRICTLY as a JSON array, no markdown, no extra text:
[
  {{
    "improvement": "<one concrete improvement>",
    "target": "business" | "system",
    "pillar": "research|content|commerce|monetization|account",
    "metric": "<before> -> <after>",
    "why": "<evidence from the inputs>"
  }}
]"""


def _parse(text: str) -> list[dict[str, str]]:
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    out: list[dict[str, str]] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        improvement = str(item.get("improvement", "")).strip()
        if not improvement:
            continue
        out.append({
            "improvement": improvement[:240],
            "target": str(item.get("target", "business")).strip().lower(),
            "pillar": str(item.get("pillar", "research")).strip().lower(),
            "metric": str(item.get("metric", ""))[:120],
            "why": str(item.get("why", ""))[:160],
        })
    return out


def improve(
    agent,
    workspace: str = "default",
    *,
    system: bool = False,
    limit: int = 4,
    tier: str = "normal",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Evidence -> gated improvement proposals (business and/or system)."""
    memory = agent.memory
    evidence: list[str] = ["### Real goals (gaps)"]
    if memory is not None:
        from .focus import focus_pack

        pack = focus_pack(memory, workspace, tier=tier)
        if pack.objectives:
            evidence += [
                f"- {o['title']} | {o['kpi']}: {o['current']:.0f}/{o['target']:.0f}"
                f" | progress {o['progress'] * 100:.0f}%"
                for o in pack.objectives
            ]
        else:
            evidence.append("- (no objectives - intelligence without goals is noise)")
        from .lessons import lessons

        items = lessons(memory, workspace)
        if items:
            evidence.append("### Lessons (work memory)")
            evidence += [f"- {i['lesson']}" for i in items[:5]]
        failed = [p.as_dict() for p in memory.procedures(workspace)
                  if p.fail_count > 0]
        if failed:
            evidence.append("### Procedures that failed (fix these)")
            evidence += [
                f"- {p['name']} (ok={p['success_count']}, fail={p['fail_count']})"
                for p in failed[:5]
            ]
    if repo_root is not None:
        try:
            from .attach import drift_report

            drift = drift_report(Path.cwd(), repo_root)
            if drift:
                evidence.append("### Contract drift (re-sync)")
                evidence += [f"- {d}" for d in drift]
        except Exception:  # noqa: BLE001 - enhancement, never fatal
            pass

    prompt = _IMPROVE_PROMPT.format(limit=max(1, limit)) + (
        f"\n\nEvidence (workspace: {workspace}, tier: {tier}):\n"
        + "\n".join(evidence)
        + ("\n\nFOCUS the proposals on improving THE FOCUX SYSTEM itself "
           "(its runtime, metaskill, workflow, tests)." if system else "")
    )
    text = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's success governor. Improvements must be "
        "concrete, measurable (before -> after) and honest. Never invent "
        "evidence. Money proposals are never auto-approved."
    ))
    proposals = _parse(text)[:limit]
    gated: list[dict[str, str]] = []
    for prop in proposals:
        result = agent.propose(pillar=prop["pillar"],
                               objective=prop["improvement"])
        gated.append({**prop, "decision": str(result.decision)})
    if memory is not None:
        for prop in gated:
            memory.remember_event(workspace, "improve", {
                "improvement": prop["improvement"],
                "target": prop["target"],
                "decision": prop["decision"],
            })
    return {"improvements": gated, "note": ""}


def format_improve(report: dict[str, Any]) -> str:
    lines = ["IMPROVE - success governor (better at all hours, always measured):"]
    for item in report["improvements"]:
        lines.append(
            f"  [{item['decision']}] ({item['target']}/{item['pillar']}) "
            f"{item['improvement']}"
            + (f" | metric: {item['metric']}" if item.get("metric") else "")
            + (f" | why: {item['why']}" if item.get("why") else "")
        )
    if not report["improvements"]:
        lines.append("  (no parseable improvements - nothing invented)")
    reviews = [i for i in report["improvements"] if i["decision"] == "REVIEW"]
    if reviews:
        lines.append("  REVIEW improvements await human approval; stage them "
                     "with `focux work frame`.")
    return _safe("\n".join(lines))


def _safe(text: str) -> str:
    try:
        return text.encode("cp1252", errors="replace").decode("cp1252")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text.encode("ascii", errors="replace").decode("ascii")
