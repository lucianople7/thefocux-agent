"""Universal brain interface: ask ANYTHING, get an evidence-grounded answer.

THE FOCUX BRAIN as a do-anything assistant for the business:

- **ask()** — any question, answered with the brain's full directed context:
  the real goals + gaps (focus pack), the REAL absorbed signals, and the
  discipline. Read-class action (gated like everything else). The brain is
  smart ONLY toward the real goals - if there are none it says so.
- **insights()** — the opportunity analyst: given the absorbed real signals
  and the active objectives, the LLM proposes N concrete digital
  opportunities, each mapped to a pillar and passed through the money-gate
  BEFORE it is reported (never auto-authorized).

Discipline: the LLM proposes, the gate decides, the human approves REVIEW.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .focus import focus_pack, format_focus

_ASK_SYSTEM = (
    "You are THE FOCUX BRAIN, the intelligence of a business. You are smart "
    "ONLY toward the real goals. Answer with evidence and concrete next "
    "steps; never invent data you cannot see; if evidence is thin, say so "
    "and give the smallest verification step. Answer in the operator's "
    "language. Be direct - no filler."
)

_INSIGHTS_PROMPT = """Given the REAL absorbed signals and the active objectives
below, propose exactly {limit} concrete digital opportunities or insights
that move the business toward its goals. Each must be evidence-based
(grounded in the signals), specific, and mapped to a pillar:
research (analysis) | content (create) | commerce (sell) |
monetization (charge) | account (config).

Answer STRICTLY as a JSON array, no markdown, no extra text:
[
  {{
    "insight": "<one concrete opportunity>",
    "pillar": "research|content|commerce|monetization|account",
    "why": "<evidence from the signals>"
  }}
]"""


@dataclass(frozen=True)
class AskResult:
    question: str
    answer: str
    decision: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"question": self.question, "answer": self.answer,
                "decision": self.decision}


def _context(agent, workspace: str) -> str:
    """Directed context: goals + gaps (focus) + discipline note."""
    memory = agent.memory
    if memory is None:
        return ""
    pack = focus_pack(memory, workspace)
    focus_txt = format_focus(pack)
    # strip the "built" timestamp line for a cleaner prompt
    lines = focus_txt.splitlines()
    return "\n".join(l for l in lines if not l.startswith("workspace:"))


def ask(agent, question: str, workspace: str = "default") -> AskResult:
    """Ask anything; the brain answers with directed intelligence (READ)."""
    gate = agent.propose(pillar="research", objective=f"ask: {question}")
    prompt = f"{_context(agent, workspace)}\n\nQUESTION: {question}"
    answer = agent.draft(prompt, system=_ASK_SYSTEM)
    return AskResult(question=question, answer=answer,
                     decision=str(gate.decision))


def _parse_insights(text: str) -> list[dict[str, str]]:
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
        insight = str(item.get("insight", "")).strip()
        if not insight:
            continue
        out.append({
            "insight": insight[:240],
            "pillar": str(item.get("pillar", "research")).strip().lower(),
            "why": str(item.get("why", ""))[:200],
        })
    return out


def insights(agent, workspace: str = "default", *, limit: int = 3,
             tier: str = "normal") -> dict[str, Any]:
    """Opportunity analyst: real signals + goals -> gated opportunities."""
    memory = agent.memory
    if memory is None:
        return {"insights": [], "note": "no memory attached"}
    pack = focus_pack(memory, workspace, tier=tier)
    prompt = _INSIGHTS_PROMPT.format(limit=max(1, limit)) + (
        "\n\n### Absorbed signals (REAL data)\n"
        + "\n".join(f"- {s}" for s in pack.signals)
        + ("\n### Active objectives\n" if pack.objectives else "")
        + "\n".join(
            f"- {o['title']} | {o['kpi']}: {o['current']:.0f}/{o['target']:.0f}"
            for o in pack.objectives
        )
    )
    text = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's opportunity analyst. Opportunities must be "
        "evidence-based and move the business toward its real goals. Never "
        "invent signals."
    ))
    proposals = _parse_insights(text)[:limit]
    gated: list[dict[str, str]] = []
    for prop in proposals:
        result = agent.propose(pillar=prop["pillar"],
                               objective=prop["insight"])
        gated.append({**prop, "decision": str(result.decision)})
    return {"insights": gated, "note": ""}
