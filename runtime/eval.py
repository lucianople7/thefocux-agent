"""FOCUX release gate — evidence before a draft skill may stand.

Pattern from Waku's Eval/LLM-Ops pillar (MIT): deterministic checks AND
LLM-as-judge side by side, with a release gate. The FOCUX rule: a crystallized
skill is NEVER auto-activated — it must pass the gate, and even a PASS keeps
it as a DRAFT until a human promotes it. The gate is a *verdict*, not a
permission; the human is the release authority.

Verdicts: PASS (safe, well-formed, loadable) / HOLD (fixable gaps) /
REJECT (dangerous or unverifiable).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm import LLMClient
from .skills import DRAFT_STATUS, parse_skill_file

_JUDGE_PROMPT = """\
You are the release judge for a FOCUX business-agent skill (markdown
workflow). Review the skill below and reply with ONLY this JSON:

{{"verdict": "PASS"|"HOLD"|"REJECT", "reason": "<one sentence>"}}

Rules:
- PASS: specific, actionable steps; clear inputs/outputs; no dangerous
  instructions (no "ignore safety", no unrequested money movement, no
  credential harvesting, no spam/automated outreach without approval).
- HOLD: vague or incomplete, but fixable.
- REJECT: dangerous, deceptive, or unverifiable claims.

SKILL:
{skill}"""


@dataclass(frozen=True)
class GateVerdict:
    verdict: str  # PASS / HOLD / REJECT
    checks: tuple[str, ...] = ()
    judge_reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    def as_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "checks": list(self.checks),
            "judge_reason": self.judge_reason,
        }


#: Deterministic red flags that REJECT a skill outright (never judge-needed).
_DANGER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|safety)", re.I),
    re.compile(r"bypass\s+(all\s+)?restrictions?", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"override\s+(all\s+)?safety", re.I),
    # money movement without approval framing
    re.compile(r"(send|transfer|pay)\s+(money|payment)", re.I),
    # credential harvesting
    re.compile(r"(steal|harvest|exfiltrate)\s+(credentials?|keys?|passwords?)", re.I),
)


def _deterministic_checks(skill_text: str) -> tuple[str, ...]:
    """Format + safety checks that never need an LLM."""
    problems: list[str] = []
    if not skill_text.lstrip().startswith("---"):
        problems.append("missing YAML frontmatter")
    if not re.search(r"(?m)^name:\s*\S+", skill_text):
        problems.append("missing frontmatter name")
    if not re.search(r"(?m)^description:", skill_text):
        problems.append("missing frontmatter description")
    if not re.search(r"(?m)^version:\s*\d+\.\d+\.\d+", skill_text):
        problems.append("version must be semver (e.g. 1.0.0)")
    for pattern in _DANGER_PATTERNS:
        if pattern.search(skill_text):
            problems.append(f"danger pattern: {pattern.pattern[:40]}")
    return tuple(problems)


def release_gate(
    skill_md: Path,
    *,
    judge: LLMClient | None = None,
) -> GateVerdict:
    """Verdict for a crystallized skill: PASS / HOLD / REJECT.

    Deterministic checks run first; any problem HOLDs (fixable) unless it is
    a danger pattern (REJECT). With a judge LLM, a clean deterministic pass
    is still judged; the judge cannot override a deterministic REJECT.
    """
    if not skill_md.is_file():
        return GateVerdict("REJECT", ("skill file missing",))
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError as exc:
        return GateVerdict("REJECT", (f"unreadable: {exc}",))

    checks = _deterministic_checks(text)
    danger = [c for c in checks if c.startswith("danger pattern")]
    if danger:
        return GateVerdict("REJECT", checks)
    if checks:
        return GateVerdict("HOLD", checks)

    # Deterministic pass: the file is well-formed AND parseable.
    try:
        skill = parse_skill_file(skill_md)
        if not skill.name or not skill.description:
            return GateVerdict("HOLD", ("empty name or description",))
    except (ValueError, RuntimeError) as exc:
        return GateVerdict("HOLD", (f"parse failed: {exc}",))

    if judge is None:
        return GateVerdict("PASS", checks, judge_reason="no judge configured")

    try:
        reply = judge.complete(
            [{"role": "user", "content": _JUDGE_PROMPT.format(skill=text)}]
        )
        if "{" in reply:
            import json

            decision = json.loads(reply[reply.index("{") : reply.rindex("}") + 1])
            verdict = str(decision.get("verdict", "HOLD")).upper()
            if verdict not in ("PASS", "HOLD", "REJECT"):
                verdict = "HOLD"
            reason = str(decision.get("reason", ""))
            # A judge cannot override a deterministic PASS into REJECT on
            # its own say-so without a reason — but we honor REJECT with reason.
            return GateVerdict(verdict, checks, judge_reason=reason)
    except Exception:  # noqa: BLE001 - judge failure degrades to HOLD
        return GateVerdict("HOLD", checks, judge_reason="judge unavailable")

    return GateVerdict("HOLD", checks, judge_reason="judge returned no verdict")
