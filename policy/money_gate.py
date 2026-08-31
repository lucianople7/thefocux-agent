"""Deterministic money-gate policy engine.

NO LLM in the decision path. The agent proposes an Action; this engine decides
ALLOW / REVIEW (human approval required) / DENY. Approvals are single-use,
expiring, and bound byte-for-byte to one exact action (SecondSign pattern).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"  # human approval required
    DENY = "deny"


class ActionClass(str, Enum):
    READ = "read"
    CONTENT = "content"  # publishing / content distribution
    COMMERCE = "commerce"  # pricing, discounts, refunds
    MONEY = "money"  # transfers, payouts, purchases
    ACCOUNT = "account"  # credentials, config, account changes


@dataclass(frozen=True)
class PolicyRule:
    action_class: ActionClass
    #: Max amount (same unit as Action.amount); None = no amount bound.
    max_amount: float | None = None
    #: L2: allow actions within the threshold without human approval.
    auto_approve: bool = False
    #: Never allowed, regardless of other fields.
    deny_by_default: bool = False


@dataclass(frozen=True)
class Action:
    action_class: ActionClass
    amount: float = 0.0
    target: str = ""  # recipient / endpoint / account id
    idempotency_key: str = ""  # unique per logical operation


@dataclass
class Approval:
    action: Action
    expires_at: float  # unix seconds
    decision: Decision | None = None
    #: Fingerprint of the exact approved action (for the audit receipt).
    approved_exactly: str = ""

    def fingerprint(self) -> str:
        a = self.action
        return f"{a.action_class.value}:{a.amount:.2f}:{a.target}:{a.idempotency_key}"


class MoneyGate:
    def __init__(
        self,
        rules: dict[ActionClass, PolicyRule],
        approval_ttl_seconds: float = 1800.0,
    ) -> None:
        self._rules = rules
        self._ttl = approval_ttl_seconds

    def decide(self, action: Action, tainted: bool = False) -> Decision:
        """Decide an action; ``tainted`` marks untrusted content in the path.

        A tainted decision is NEVER auto-approved: any class that would
        otherwise be ALLOW or REVIEW returns REVIEW (human approval required).
        """
        rule = self._rules.get(action.action_class)
        if rule is None:
            return Decision.DENY  # unknown class denied by default
        if rule.deny_by_default:
            return Decision.DENY
        if rule.max_amount is not None and action.amount > rule.max_amount:
            return Decision.REVIEW
        if tainted:
            # Untrusted content (web pages, user text, downloaded files) is in
            # scope: the decision must not fall through to auto-approve.
            return Decision.REVIEW
        if not rule.auto_approve:
            return Decision.REVIEW
        return Decision.ALLOW

    def create_approval(self, action: Action, now: float) -> Approval:
        return Approval(action=action, expires_at=now + self._ttl)

    def approve(self, approval: Approval, action: Action, now: float) -> bool:
        """Single-use, expiring, byte-for-byte bound approval."""
        if self.decide(action) == Decision.DENY:
            return False  # a DENY-class action can never be approved
        if approval.decision is not None:
            return False  # already decided
        if now >= approval.expires_at:
            return False
        if approval.action != action:
            return False
        approval.decision = Decision.ALLOW
        approval.approved_exactly = approval.fingerprint()
        return True

    def falsification_test(self) -> bool:
        """With every rule off, no money action may be ALLOWed.

        An auto-approve rule without a bound is an unbounded ALLOW: any rule
        with auto_approve=True and deny_by_default=False MUST declare a
        max_amount, or the whole table fails. The tainted path is checked too:
        even a bounded auto-approve rule must never ALLOW a money action when
        untrusted content is in scope.
        """
        if any(
            rule.auto_approve and not rule.deny_by_default and rule.max_amount is None
            for rule in self._rules.values()
        ):
            return False
        amounts = (0.0, 1.0, 100.0, 1_000_000.0)
        untainted_ok = all(
            self.decide(Action(ActionClass.MONEY, amount=a))
            in (Decision.REVIEW, Decision.DENY)
            for a in amounts
        )
        tainted_ok = all(
            self.decide(Action(ActionClass.MONEY, amount=a), tainted=True)
            in (Decision.REVIEW, Decision.DENY)
            for a in amounts
        )
        return untainted_ok and tainted_ok
