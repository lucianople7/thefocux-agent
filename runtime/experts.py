"""The Expert Panel — world-class domain expertise the brain applies.

THE FOCUX BRAIN carries expert playbooks for the pillars it exists to win:
content, social media, ecommerce, monetization and digital opportunities.
This layer makes that expertise ACTIVE:

- **ask_expert()** — consult a domain expert: the LLM answers as a
  world-class specialist, grounded in the playbook + the REAL absorbed
  signals + the current objectives. A read-class action (gated ALLOW/REVIEW
  like any other).
- **review_draft()** — a quality gate BEFORE content/offers ship: a
  deterministic pre-check (empty/short drafts never pass) plus an
  LLM-as-judge verdict per domain checklist (hook, CTA, offer, price,
  validation...). Verdict: PASS / REVISE. This is a QUALITY verdict, never
  a permission — the money-gate and the human remain the authority.

Discipline: the playbooks are knowledge, not promises; results come from
execution + measurement. An expert opinion without evidence is a guess.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ingest import recent_signals

PLAYBOOKS_DIR = Path(__file__).resolve().parent.parent / "playbooks"

#: domain -> (expert title, checklist items for review)
EXPERTS: dict[str, dict[str, object]] = {
    "content": {
        "title": "world-class content strategist and copywriter",
        "checklist": ("hook", "cta", "evidence", "format"),
    },
    "social": {
        "title": "world-class social media growth operator",
        "checklist": ("platform", "format", "hook", "cta"),
    },
    "ecommerce": {
        "title": "world-class ecommerce operator (unit economics)",
        "checklist": ("offer", "price", "audience", "path"),
    },
    "monetization": {
        "title": "world-class monetization strategist",
        "checklist": ("ladder", "price", "honesty", "cta"),
    },
    "opportunities": {
        "title": "world-class digital opportunity analyst",
        "checklist": ("demand", "validation", "launch", "metrics"),
    },
}

_MIN_REVIEW_LENGTH = 40  # below this a draft is "too thin" without a judge


def list_experts() -> list[dict[str, str]]:
    out = []
    for domain, meta in EXPERTS.items():
        playbook = PLAYBOOKS_DIR / f"{domain}.md"
        out.append({
            "domain": domain,
            "title": str(meta["title"]),
            "playbook": str(playbook) if playbook.exists() else "",
        })
    return out


def _playbook(domain: str) -> str:
    path = PLAYBOOKS_DIR / f"{domain}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _context(agent, workspace: str) -> str:
    """Real absorbed signals + active objectives (the evidence for experts)."""
    parts: list[str] = []
    memory = agent.memory
    if memory is not None:
        signals = recent_signals(memory, workspace, per_source=2)
        if signals:
            parts.append("### Absorbed signals (REAL data)")
            parts += [f"- {s}" for s in signals]
        objs = memory.objectives(workspace)
        if objs:
            parts.append("### Active objectives")
            parts += [
                f"- {o.title} | {o.kpi}: {o.current:.0f}/{o.target:.0f}"
                for o in objs
            ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ask_expert: consult a domain expert (read-class, gated)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpertAnswer:
    domain: str
    question: str
    answer: str
    decision: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"domain": self.domain, "question": self.question,
                "answer": self.answer, "decision": self.decision}


def ask_expert(agent, domain: str, question: str,
               workspace: str = "default") -> ExpertAnswer:
    """Consult a world-class expert for the domain, grounded in playbook +
    real signals + objectives. Read-class: gated like any action."""
    meta = EXPERTS.get(domain)
    if meta is None:
        raise ValueError(f"unknown expert domain: {domain} "
                         f"(known: {', '.join(EXPERTS)})")
    gate = agent.propose(pillar="research", objective=f"consult expert: {question}")
    system = (
        f"You are THE FOCUX BRAIN operating as a {meta['title']}. "
        "Answer with the rigor of a top-tier specialist: concrete, "
        "evidence-based, actionable. Never invent data you cannot see; if "
        "evidence is thin, say so and give the smallest verification step. "
        "Be direct - no filler, no hedging.\n\n"
        "## Your playbook (operating knowledge)\n"
        f"{_playbook(domain)}"
    )
    user = f"{_context(agent, workspace)}\n\nQUESTION: {question}"
    answer = agent.draft(user, system=system)
    return ExpertAnswer(domain=domain, question=question, answer=answer,
                        decision=str(gate.decision))


# ---------------------------------------------------------------------------
# review_draft: quality gate (deterministic + LLM judge) — PASS / REVISE
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReviewItem:
    item: str
    passed: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {"item": self.item, "passed": self.passed, "reason": self.reason}


@dataclass(frozen=True)
class ReviewVerdict:
    domain: str
    verdict: str  # PASS / REVISE
    items: tuple[ReviewItem, ...] = ()
    judge_reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "verdict": self.verdict,
            "items": [i.as_dict() for i in self.items],
            "judge_reason": self.judge_reason,
        }


_REVIEW_PROMPT = """\
You are the quality judge for a {title}. Review the DRAFT below against the
checklist. Reply with ONLY this JSON:

{{"items": [{{"item": "<name>", "passed": true|false, "reason": "<one sentence>"}}], "verdict": "PASS"|"REVISE", "reason": "<one sentence>"}}

Checklist: {checklist}
Rules: PASS when at least 60% of items pass; REVISE otherwise. Be strict -
a world-class operator would not ship a draft that fails the checklist.
Ground every pass/fail in the actual draft text.

DRAFT:
{draft}"""


def review_draft(agent, domain: str, draft: str,
                 workspace: str = "default") -> ReviewVerdict:
    """Quality gate for content/offers BEFORE they ship.

    Deterministic pre-check: empty or too-thin drafts REVISE without calling
    the judge. Then an LLM-as-judge scores the domain checklist. The verdict
    is quality advice - the money-gate and the human stay the authority.
    """
    meta = EXPERTS.get(domain)
    if meta is None:
        raise ValueError(f"unknown expert domain: {domain}")
    draft = (draft or "").strip()
    if len(draft) < _MIN_REVIEW_LENGTH:
        return ReviewVerdict(
            domain=domain, verdict="REVISE",
            items=(ReviewItem("length", False,
                              "too thin to review (< 40 chars)"),),
            judge_reason="deterministic pre-check",
        )
    checklist = ", ".join(str(c) for c in meta["checklist"])
    prompt = _REVIEW_PROMPT.format(
        title=meta["title"], checklist=checklist, draft=draft[:4000]
    )
    text = agent.draft(prompt, system=(
        f"You are THE FOCUX BRAIN's quality judge for {meta['title']}. "
        "Strict, specific, evidence-based. Never invent checklist results."
    ))
    return _parse_review(domain, text, checklist)


def _parse_review(domain: str, text: str, checklist: str) -> ReviewVerdict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return ReviewVerdict(
            domain=domain, verdict="REVISE",
            judge_reason="judge returned unparseable output",
        )
    import json

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return ReviewVerdict(
            domain=domain, verdict="REVISE",
            judge_reason="judge returned unparseable output",
        )
    items = tuple(
        ReviewItem(str(i.get("item", "?")), bool(i.get("passed", False)),
                   str(i.get("reason", ""))[:160])
        for i in data.get("items", []) if isinstance(i, dict)
    )
    if not items:
        return ReviewVerdict(
            domain=domain, verdict="REVISE",
            judge_reason="judge returned no checklist items",
        )
    passed = sum(1 for i in items if i.passed)
    verdict = "PASS" if (passed / len(items)) >= 0.6 else "REVISE"
    return ReviewVerdict(
        domain=domain, verdict=verdict, items=items,
        judge_reason=str(data.get("reason", "") or "")[:200],
    )
