"""Money-gate CLI — the deterministic enforcement binary a shell can call.

Usage (from the project root, with python on PATH):

  # The agent proposes BEFORE any money/publish/account action:
  python policy/money_gate_cli.py decide --class MONEY --amount 100.00 \
      --target stripe --idempotency-key k1 [--tainted]

  # The human (command owner) approves a parked action:
  python policy/money_gate_cli.py approve --class MONEY --amount 100.00 \
      --target stripe --idempotency-key k1 [--now <unix>]

Exit codes: 0 = ALLOW (approved), 1 = REVIEW (needs human), 2 = DENY,
3 = usage/config error. Output is one JSON line on stdout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from money_gate import (  # noqa: E402
    Action,
    ActionClass,
    Decision,
    MoneyGate,
    PolicyRule,
)

# L1 defaults: every class REVIEWs; ACCOUNT is deny-by-default; nothing is
# auto-approved. Operators tighten/loosen per class here (L2) — the engine
# enforces the falsification invariant regardless.
L1_RULES: dict[ActionClass, PolicyRule] = {
    ActionClass.READ: PolicyRule(ActionClass.READ),
    ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
    ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
    ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
    ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT, deny_by_default=True),
}

GATE = MoneyGate(L1_RULES)


def _action(args: argparse.Namespace) -> Action:
    return Action(
        action_class=ActionClass(args.action_class),
        amount=args.amount,
        target=args.target,
        idempotency_key=args.idempotency_key,
    )


def _out(decision: Decision, extra: dict | None = None) -> None:
    payload = {"decision": decision.value}
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=True))


def _deny(reason: str) -> int:
    _out(Decision.DENY, {"reason": reason})
    return 2


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="money_gate")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decide")
    d.add_argument("--class", dest="action_class", required=True,
                   choices=[c.value for c in ActionClass])
    d.add_argument("--amount", type=float, default=0.0)
    d.add_argument("--target", default="")
    d.add_argument("--idempotency-key", default="")
    d.add_argument("--tainted", action="store_true",
                   help="untrusted content is in scope: never auto-approve")

    a = sub.add_parser("approve")
    a.add_argument("--class", dest="action_class", required=True,
                   choices=[c.value for c in ActionClass])
    a.add_argument("--amount", type=float, default=0.0)
    a.add_argument("--target", default="")
    a.add_argument("--idempotency-key", default="")
    a.add_argument("--now", type=float, default=None)

    args = p.parse_args(argv)
    action = _action(args)

    if args.command == "decide":
        decision = GATE.decide(action, tainted=args.tainted)
        if decision is Decision.ALLOW:
            _out(decision)
            return 0
        if decision is Decision.DENY:
            _out(decision, {"reason": "class denied by policy"})
            return 2
        _out(decision, {"reason": "human approval required"})
        return 1

    # approve — the human-consent path. Shells must only expose this to the
    # command owner, never to the agent itself.
    decision = GATE.decide(action)
    if decision is Decision.DENY:
        return _deny("cannot approve a denied action")
    approval = GATE.create_approval(action, now=args.now or 0.0)
    ok = GATE.approve(approval, action, now=args.now or 0.0)
    _out(Decision.ALLOW if ok else Decision.REVIEW, {
        "approved_exactly": approval.approved_exactly,
    })
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
