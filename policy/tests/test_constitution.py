"""Tests for policy/constitution.py — the three laws as code."""
from __future__ import annotations

import pytest

from policy.constitution import (
    LAW_HIERARCHY,
    Claim,
    Law,
    apply_constitution,
    check_law1,
    check_law2,
    check_law3,
    law1_blocks,
)
from policy.money_gate import (
    Action,
    ActionClass,
    Decision,
    MoneyGate,
    PolicyRule,
)


def _gate() -> MoneyGate:
    """A realistic L1/L2 rule table: money REVIEW, content/commerce REVIEW,
    read auto-approve, account REVIEW."""
    return MoneyGate(
        {
            ActionClass.READ: PolicyRule(ActionClass.READ, auto_approve=True),
            ActionClass.CONTENT: PolicyRule(
                ActionClass.CONTENT, max_amount=0.0, auto_approve=True
            ),
            ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE, max_amount=50.0),
            ActionClass.MONEY: PolicyRule(ActionClass.MONEY, max_amount=100.0),
            ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
        }
    )


def test_law_hierarchy_order() -> None:
    assert LAW_HIERARCHY[0] is Law.I
    assert LAW_HIERARCHY[1] is Law.II
    assert LAW_HIERARCHY[2] is Law.III


def test_law1_money_never_allows() -> None:
    gate = _gate()
    verdict = check_law1(
        gate, Action(ActionClass.MONEY, amount=5.0, target="payout")
    )
    assert verdict.passed  # REVIEW is fine; ALLOW would fail
    assert verdict.evidence.startswith("decision=")


def test_law1_blocks_on_unbounded_allow() -> None:
    # An auto-approve money rule with no bound is a constitution violation.
    bad_gate = MoneyGate(
        {ActionClass.MONEY: PolicyRule(ActionClass.MONEY, auto_approve=True)}
    )
    verdict = check_law1(bad_gate, Action(ActionClass.MONEY, amount=1.0))
    assert not verdict.passed
    assert "ALLOW" in verdict.evidence


def test_law1_tainted_never_allows() -> None:
    # Tainted content downgrades to REVIEW inside the gate; Law I must never
    # see a tainted ALLOW (the gate already protects, so the verdict passes).
    gate = MoneyGate(
        {ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT, auto_approve=True)}
    )
    assert gate.decide(
        Action(ActionClass.CONTENT, amount=0.0, target="publish"), tainted=True
    ) == Decision.REVIEW
    verdict = check_law1(
        gate,
        Action(ActionClass.CONTENT, amount=0.0, target="publish"),
        tainted=True,
    )
    assert verdict.passed
    assert "review" in verdict.evidence


def test_law1_blocks_unbounded_tainted_allow() -> None:
    # If a future gate ever ALLOWs tainted content, Law I fails hard.
    class BrokenGate(MoneyGate):
        def decide(self, action, tainted=False):  # type: ignore[override]
            return Decision.ALLOW

    verdict = check_law1(
        BrokenGate({}),
        Action(ActionClass.CONTENT, amount=0.0, target="publish"),
        tainted=True,
    )
    assert not verdict.passed
    assert "tainted content in scope would ALLOW" in verdict.evidence


def test_law2_spam_signals() -> None:
    assert check_law2("Real framework, real results").passed
    bad = check_law2("Click here and get free money now!")
    assert not bad.passed
    assert "spam signals" in bad.evidence
    assert "click here" in bad.evidence
    assert "free money" in bad.evidence


def test_law2_empty_content_is_fine() -> None:
    # Empty content has no spam signals; the quality-gate handles substance.
    assert check_law2("").passed


def test_law3_claims_need_evidence() -> None:
    ok = check_law3(
        (Claim("Impressions grew", "receipts/2026-08-28-metrics.md"),)
    )
    assert ok.passed
    bad = check_law3((Claim("Impressions grew", ""),))
    assert not bad.passed
    assert "without evidence" in bad.evidence


def test_apply_constitution_full() -> None:
    gate = _gate()
    verdicts = apply_constitution(
        gate,
        Action(ActionClass.CONTENT, amount=0.0, target="publish"),
        content="Honest framework breakdown",
        claims=(Claim("Based on our data", "receipts/x.md"),),
    )
    assert len(verdicts) == 3
    assert all(v.passed for v in verdicts)
    # Ordered by hierarchy: Law I first.
    assert verdicts[0].law is Law.I
    assert not law1_blocks(verdicts)


def test_apply_constitution_law1_absolute() -> None:
    bad_gate = MoneyGate(
        {ActionClass.MONEY: PolicyRule(ActionClass.MONEY, auto_approve=True)}
    )
    verdicts = apply_constitution(
        bad_gate,
        Action(ActionClass.MONEY, amount=1.0),
        content="anything",
        claims=(),
    )
    assert law1_blocks(verdicts)
    # Even with Law II and III passing, Law I failure is absolute.
    assert verdicts[0].law is Law.I
    assert not verdicts[0].passed


def test_constitution_never_approves_money_any_amount() -> None:
    """The falsification-style invariant through the constitution."""
    gate = _gate()
    for amount in (0.0, 0.01, 1.0, 100.0, 1_000_000.0):
        verdict = check_law1(gate, Action(ActionClass.MONEY, amount=amount))
        assert verdict.passed  # REVIEW/DENY, never ALLOW
        assert gate.decide(Action(ActionClass.MONEY, amount=amount)) in (
            Decision.REVIEW,
            Decision.DENY,
        )
