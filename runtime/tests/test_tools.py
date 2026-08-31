"""Tests for the FOCUX tool layer — every tool gated before execution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, Decision, MoneyGate, PolicyRule  # noqa: E402
from runtime.tools import ToolRegistry, ToolResult, ToolSpec  # noqa: E402


def _gate() -> MoneyGate:
    return MoneyGate(
        {
            ActionClass.READ: PolicyRule(
                ActionClass.READ, max_amount=0.0, auto_approve=True
            ),
            ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
            ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
            ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
            ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
        }
    )


def test_ping_auto_allows() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("ping", {})
    assert result.decision == "ALLOW"
    assert result.output == "pong"


def test_publish_post_is_review() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("publish_post", {"platform": "linkedin"})
    assert result.decision == "REVIEW"
    assert "approve exactly" in result.approval_hint
    # The tool NEVER ran: output is the card, not a publish confirmation.
    assert "PUBLISHED" not in result.output


def test_make_payment_never_executes_without_approval() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("make_payment", {"amount": 100.0, "to": "vendor"})
    assert result.decision == "REVIEW"
    assert "PAYMENT" not in result.output


def test_unknown_tool_denied() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("no_such_tool", {})
    assert result.decision == "DENY"
    assert not result.ok


def test_tainted_request_never_allows() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("ping", {}, tainted=True)
    # tainted downgrades even a READ tool to REVIEW (gate contract)
    assert result.decision == "REVIEW"
    assert "pong" not in result.output


def test_custom_tool_registration() -> None:
    reg = ToolRegistry(gate=_gate())

    def handler(args):
        return f"ran {args.get('x')}"

    reg.register(
        ToolSpec("my_tool", "custom", ActionClass.READ, {"x": {"type": "string"}}),
        handler,
    )
    assert reg.request("my_tool", {"x": "1"}) == ToolResult(True, "ALLOW", "ran 1")
    assert "my_tool" in reg.tool_names()


def test_schemas_expose_tools_to_llm() -> None:
    reg = ToolRegistry(gate=_gate())
    schemas = reg.schemas()
    names = {s["function"]["name"] for s in schemas}
    assert {"ping", "publish_post", "make_payment"}.issubset(names)
    # money tool is present in the schema but never executes without approval
    payment = next(s for s in schemas if s["function"]["name"] == "make_payment")
    assert "amount" in payment["function"]["parameters"]["properties"]


def test_falsification_holds_with_tools() -> None:
    reg = ToolRegistry(gate=_gate())
    assert reg._gate.falsification_test() is True


def test_law1_denies_on_broken_gate() -> None:
    bad = MoneyGate(
        {ActionClass.MONEY: PolicyRule(ActionClass.MONEY, auto_approve=True)}
    )
    reg = ToolRegistry(gate=bad)
    result = reg.request("make_payment", {"amount": 1.0, "to": "x"})
    assert result.decision == "DENY"
    assert "Law I" in result.output
