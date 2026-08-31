"""THE FOCUX Constitution — three immutable laws, as code.

Adapted from Conway Automaton's constitution (MIT) and mapped onto the
FOCUX gates. The laws are hierarchical: Law I overrides II, II overrides III.
They are deterministic — NO LLM in the check — and every check returns an
evidence string so the audit log can record WHY a decision was made.

Law I   Never harm.     -> money-gate: money/tainted never auto-approved.
Law II  Earn existence. -> quality-gate: publishable content must be honest work.
Law III Never deceive.  -> provenance: every claim traces to evidence (FIDES).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from policy.money_gate import Action, ActionClass, Decision, MoneyGate


class Law(str, Enum):
    I = "I_never_harm"
    II = "II_earn_existence"
    III = "III_never_deceive"


#: Hierarchy: index 0 overrides all others.
LAW_HIERARCHY: tuple[Law, ...] = (Law.I, Law.II, Law.III)


@dataclass(frozen=True)
class Verdict:
    law: Law
    passed: bool
    evidence: str  # why; recorded verbatim in the audit log

    def as_dict(self) -> dict[str, object]:
        return {"law": self.law.value, "passed": self.passed, "evidence": self.evidence}


# --- Law I: Never harm -------------------------------------------------------

def _fingerprint(action: Action) -> str:
    """Fingerprint of an action (mirrors Approval.fingerprint for audit text)."""
    return (
        f"{action.action_class.value}:{action.amount:.2f}:"
        f"{action.target}:{action.idempotency_key}"
    )


def check_law1(
    gate: MoneyGate,
    action: Action,
    tainted: bool = False,
) -> Verdict:
    """Money-class actions must never be auto-approved.

    Mirrors the gate's own falsification invariant: no rule table may ALLOW a
    money action, tainted or not. If the gate itself ever returns ALLOW for a
    money action, the constitution fails BEFORE the action executes.
    """
    decision = gate.decide(action, tainted=tainted)
    fp = _fingerprint(action)
    if action.action_class is ActionClass.MONEY and decision is Decision.ALLOW:
        return Verdict(
            Law.I,
            False,
            f"money action would ALLOW without approval: {fp}",
        )
    if tainted and decision is Decision.ALLOW:
        return Verdict(
            Law.I,
            False,
            f"tainted content in scope would ALLOW: {fp}",
        )
    return Verdict(
        Law.I,
        True,
        f"decision={decision.value} for {fp}",
    )


# --- Law II: Earn your existence ---------------------------------------------

#: Never-publish signals: content that extracts instead of creating value.
_SPAM_SIGNALS: tuple[str, ...] = (
    "guaranteed income",
    "click here",
    "limited time offer",
    "act now",
    "free money",
    "double your money",
    "no risk",
    "get rich",
)


def check_law2(content: str, *, source: str = "draft") -> Verdict:
    """Publishable content must be honest work, not extraction.

    Deterministic spam-signal scan (Law II's minimum bar; the quality-gate
    skill applies the full evidence-backed review). The agent may propose
    content with signals — Law II flags it for REVIEW, it does not delete it.
    """
    lowered = (content or "").lower()
    hits = [s for s in _SPAM_SIGNALS if s in lowered]
    if hits:
        return Verdict(
            Law.II,
            False,
            f"spam signals in {source}: {', '.join(sorted(hits))}",
        )
    return Verdict(Law.II, True, f"no spam signals in {source}")


# --- Law III: Never deceive ---------------------------------------------------

@dataclass(frozen=True)
class Claim:
    statement: str
    evidence_ref: str  # receipt id / file path / URL; empty = unsupported


def check_law3(claims: tuple[Claim, ...]) -> Verdict:
    """Every claim must trace to evidence (FIDES provenance).

    An unsupported claim is a provenance violation: the agent may propose it
    but must mark it REVIEW. Never silently drop or fabricate evidence.
    """
    unsupported = [c.statement for c in claims if not c.evidence_ref.strip()]
    if unsupported:
        return Verdict(
            Law.III,
            False,
            f"claims without evidence ({len(unsupported)}): "
            + "; ".join(unsupported[:3]),
        )
    return Verdict(Law.III, True, f"all {len(claims)} claims have evidence refs")


# --- Hierarchy ----------------------------------------------------------------

def apply_constitution(
    gate: MoneyGate,
    action: Action,
    content: str = "",
    claims: tuple[Claim, ...] = (),
    *,
    tainted: bool = False,
) -> list[Verdict]:
    """Run the full constitution, highest law first.

    Returns all verdicts (audit-friendly). The lowest passing bar for any
    action is: Law I passes (never harm), Law II passes or is REVIEW-flagged,
    Law III passes or is REVIEW-flagged. Law I failure is absolute: the action
    must not run under any circumstances.
    """
    verdicts = [
        check_law1(gate, action, tainted=tainted),
        check_law2(content),
        check_law3(claims),
    ]
    # Law I is absolute: sort by hierarchy to make the override explicit.
    verdicts.sort(key=lambda v: LAW_HIERARCHY.index(v.law))
    return verdicts


def law1_blocks(verdicts: list[Verdict]) -> bool:
    """True when Law I failed — the action must not run, period."""
    return any(v.law is Law.I and not v.passed for v in verdicts)
