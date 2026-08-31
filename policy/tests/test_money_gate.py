"""Money-gate policy engine -- deterministic, no LLM."""
from __future__ import annotations

from policy.money_gate import Action, ActionClass, Decision, MoneyGate, PolicyRule

L1_RULES = {
    ActionClass.READ: PolicyRule(ActionClass.READ),
    ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
    ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
    ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
    ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT, deny_by_default=True),
}


def _gate(overrides: dict | None = None) -> MoneyGate:
    rules = {**L1_RULES, **(overrides or {})}
    return MoneyGate(rules)


def test_unknown_action_class_is_denied() -> None:
    assert _gate().decide(Action("unknown")) == Decision.DENY


def test_read_actions_review_at_l1() -> None:
    # L1: nothing is auto-approved; reads still route to the approval card.
    assert _gate().decide(Action(ActionClass.READ)) == Decision.REVIEW


def test_money_always_review_at_l1() -> None:
    gate = _gate()
    for amount in (0.0, 1.0, 100.0, 1_000_000.0):
        assert gate.decide(Action(ActionClass.MONEY, amount=amount)) == Decision.REVIEW


def test_amount_below_threshold_allows_when_auto_approve_l2() -> None:
    gate = _gate(
        {
            ActionClass.COMMERCE: PolicyRule(
                ActionClass.COMMERCE, max_amount=50.0, auto_approve=True
            )
        }
    )
    assert gate.decide(Action(ActionClass.COMMERCE, amount=10.0)) == Decision.ALLOW
    assert gate.decide(Action(ActionClass.COMMERCE, amount=50.0)) == Decision.ALLOW
    assert gate.decide(Action(ActionClass.COMMERCE, amount=50.01)) == Decision.REVIEW


def test_deny_by_default_class_never_allows() -> None:
    gate = _gate()
    assert gate.decide(Action(ActionClass.ACCOUNT)) == Decision.DENY
    # Even an L2 auto-approve rule cannot override deny_by_default.
    assert (
        _gate(
            {
                ActionClass.ACCOUNT: PolicyRule(
                    ActionClass.ACCOUNT, auto_approve=True, deny_by_default=True
                )
            }
        ).decide(Action(ActionClass.ACCOUNT))
        == Decision.DENY
    )


def test_tainted_never_allows_even_with_auto_approve() -> None:
    gate = _gate(
        {
            ActionClass.COMMERCE: PolicyRule(
                ActionClass.COMMERCE, max_amount=100.0, auto_approve=True
            )
        }
    )
    action = Action(ActionClass.COMMERCE, amount=10.0)
    # Untainted, the bounded auto-approve rule allows.
    assert gate.decide(action) == Decision.ALLOW
    # Untrusted content in the decision path: never auto-approve.
    assert gate.decide(action, tainted=True) == Decision.REVIEW


def test_tainted_money_always_review() -> None:
    gate = _gate()
    for amount in (0.0, 1.0, 100.0, 1_000_000.0):
        assert (
            gate.decide(Action(ActionClass.MONEY, amount=amount), tainted=True)
            == Decision.REVIEW
        )


def test_tainted_deny_by_default_stays_deny() -> None:
    gate = _gate()
    assert gate.decide(Action(ActionClass.ACCOUNT), tainted=True) == Decision.DENY


def test_approve_denies_deny_class_action() -> None:
    """A human-consent surface misconfiguration must not approve a DENY action."""
    gate = _gate()
    action = Action(ActionClass.ACCOUNT)  # deny_by_default in L1_RULES
    approval = gate.create_approval(action, now=1_000.0)
    assert gate.decide(action) == Decision.DENY
    assert gate.approve(approval, action, now=1_000.0) is False


def test_approval_single_use() -> None:
    gate = _gate()
    action = Action(ActionClass.MONEY, amount=25.0, target="stripe", idempotency_key="k1")
    approval = gate.create_approval(action, now=1_000.0)
    assert gate.approve(approval, action, now=1_000.0) is True
    assert gate.approve(approval, action, now=1_000.0) is False


def test_approval_expires() -> None:
    gate = _gate()
    action = Action(ActionClass.MONEY, amount=25.0)
    approval = gate.create_approval(action, now=1_000.0)
    assert gate.approve(approval, action, now=1_000.0 + 1_801.0) is False


def test_approval_bound_to_exact_action() -> None:
    gate = _gate()
    approved_action = Action(ActionClass.MONEY, amount=25.0, target="stripe")
    other_action = Action(ActionClass.MONEY, amount=26.0, target="stripe")
    approval = gate.create_approval(approved_action, now=1_000.0)
    # A different amount or target must NOT pass with this approval.
    assert gate.approve(approval, other_action, now=1_000.0) is False
    assert gate.approve(approval, approved_action, now=1_000.0) is True


def test_falsification_gate_off_means_no_money_moves() -> None:
    """The boundary must hold even if every rule is turned off."""
    gate = MoneyGate({})  # empty rules: nothing known, nothing allowed
    assert gate.falsification_test() is True
    assert gate.decide(Action(ActionClass.MONEY, amount=1.0)) == Decision.DENY


def test_default_l1_gate_passes_falsification() -> None:
    assert _gate().falsification_test() is True


def test_approval_bound_to_target_and_idempotency_key() -> None:
    gate = _gate()
    approved = Action(
        ActionClass.MONEY, amount=25.0, target="stripe", idempotency_key="k1"
    )
    approval = gate.create_approval(approved, now=1_000.0)
    # Same amount but a different target or a different idempotency key: reject.
    for other in (
        Action(ActionClass.MONEY, amount=25.0, target="paypal", idempotency_key="k1"),
        Action(ActionClass.MONEY, amount=25.0, target="stripe", idempotency_key="k2"),
    ):
        assert gate.approve(approval, other, now=1_000.0) is False


def test_falsification_rejects_unbounded_auto_approve() -> None:
    gate = MoneyGate(
        {ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE, auto_approve=True)}
    )
    assert gate.falsification_test() is False


def test_falsification_with_tainted() -> None:
    """A bounded auto-approve rule passes the unbounded-invariant check, but a
    money action would auto-approve if taint were ignored: the tainted path
    forces REVIEW and falsification must reject the table."""
    gate = MoneyGate(
        {
            ActionClass.MONEY: PolicyRule(
                ActionClass.MONEY, max_amount=100.0, auto_approve=True
            )
        }
    )
    # The tainted path must never fall through to the auto-approve ALLOW.
    assert (
        gate.decide(Action(ActionClass.MONEY, amount=10.0), tainted=True)
        == Decision.REVIEW
    )
    assert gate.falsification_test() is False


def test_approval_expired_at_exact_expiry() -> None:
    gate = _gate()
    action = Action(ActionClass.MONEY, amount=25.0)
    approval = gate.create_approval(action, now=1_000.0)
    # expires_at == now + TTL; at exactly expires_at the approval is expired.
    assert gate.approve(approval, action, now=1_000.0 + 1_800.0) is False
