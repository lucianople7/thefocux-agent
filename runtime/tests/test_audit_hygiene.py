"""Tests for audit hygiene (secret redaction) + dry-run policy mode.

Patterns absorbed from CopilotKit OpenBot (MIT): secrets never enter the
audit trail, and dry-run mode decides-and-records without enforcing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402
from runtime.redact import redact_json, redact_mapping, redact_text, redact_value  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


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


# --- redaction ---------------------------------------------------------------

def test_redact_sensitive_keys() -> None:
    assert redact_value("api_key", "sk-1234567890") == "<redacted:13>"
    assert redact_value("prompt", "draft a post") == "<redacted:12>"
    assert redact_value("topic", "AI agents") == "AI agents"  # not sensitive


def test_redact_text_high_entropy() -> None:
    assert redact_text("key is sk-abcdefghijklmnop") == "key is <redacted>"
    assert redact_text("Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIx") == "Bearer <redacted>"
    assert redact_text("normal text") == "normal text"


def test_redact_mapping_nested() -> None:
    data = {
        "platform": "linkedin",
        "credentials": {"token": "sk-abcdefghijkl", "client_id": "abc"},
        "message": "Bearer abcdefghijklmnop",
    }
    out = redact_mapping(data)
    assert out["platform"] == "linkedin"
    # "credentials" is a fully sensitive key -> whole subtree redacted.
    assert out["credentials"] == "<redacted>"
    assert out["message"] == "Bearer <redacted>"  # label kept, secret gone


def test_redact_json_roundtrip() -> None:
    text = '{"api_key": "sk-abcdefghijklmnop", "topic": "AI"}'
    out = redact_json(text)
    assert "sk-abcdefghijklmnop" not in out
    assert '"AI"' in out


def test_tool_request_redacts_args_from_output() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request(
        "update_credentials",
        {"target": "stripe", "secret": "sk-live-abcdefghijklmnop"},
    )
    # REVIEW path: hint must not contain the secret.
    assert result.decision == "REVIEW"
    assert "sk-live-abcdefghijklmnop" not in result.output
    assert "sk-live-abcdefghijklmnop" not in result.approval_hint


# --- dry-run -----------------------------------------------------------------

def test_dry_run_runs_through_review() -> None:
    reg = ToolRegistry(gate=_gate())
    # publish_post is REVIEW at L1; dry_run lets it run and marks it.
    result = reg.request("publish_post", {"platform": "linkedin"}, dry_run=True)
    assert result.decision == "ALLOW"
    assert "DRY-RUN" in result.output
    assert "would have been review" in result.output


def test_dry_run_never_overrides_deny() -> None:
    reg = ToolRegistry(gate=_gate())
    result = reg.request("no_such_tool", {}, dry_run=True)
    assert result.decision == "DENY"
    assert not result.ok


def test_dry_run_never_overrides_law1() -> None:
    bad = MoneyGate(
        {ActionClass.MONEY: PolicyRule(ActionClass.MONEY, auto_approve=True)}
    )
    reg = ToolRegistry(gate=bad)
    result = reg.request("make_payment", {"amount": 1.0, "to": "x"}, dry_run=True)
    assert result.decision == "DENY"
    assert "Law I" in result.output
