"""Tests for the FOCUX Orchestrator — 9 specialized roles with schedules."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, Decision, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from runtime.orchestrator import (  # noqa: E402
    ROLES,
    all_roles,
    due_roles,
    next_due_in,
    role_due,
    role_named,
)


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


class _StubLLM:
    def complete(self, messages):  # type: ignore[no-untyped-def]
        return "role draft output"


def test_eleven_roles() -> None:
    roles = all_roles()
    assert len(roles) == 11
    names = {r.name for r in roles}
    assert names == {
        "orchestrator", "planning", "competitor-research", "social-media",
        "email-outreach", "customer-support", "ads", "code", "finance",
        "evolution", "multiplier",
    }


def test_roles_have_action_classes() -> None:
    by_name = {r.name: r for r in all_roles()}
    assert by_name["finance"].action_class is ActionClass.MONEY
    assert by_name["social-media"].action_class is ActionClass.CONTENT
    assert by_name["ads"].action_class is ActionClass.COMMERCE
    assert by_name["code"].action_class is ActionClass.ACCOUNT
    assert by_name["orchestrator"].action_class is ActionClass.READ


def test_role_named() -> None:
    assert role_named("social-media") is not None
    assert role_named("nope") is None


def test_clock_cadence_due() -> None:
    role = role_named("orchestrator")
    assert role is not None
    assert role_due(role, datetime(2026, 8, 31, 6, 0)) is True
    assert role_due(role, datetime(2026, 8, 31, 20, 0)) is True
    assert role_due(role, datetime(2026, 8, 31, 12, 0)) is False


def test_interval_cadence_due() -> None:
    role = role_named("social-media")  # every 2h
    assert role is not None
    assert role_due(role, datetime(2026, 8, 31, 8, 0)) is True
    assert role_due(role, datetime(2026, 8, 31, 10, 0)) is True
    assert role_due(role, datetime(2026, 8, 31, 9, 0)) is False  # wrong hour
    assert role_due(role, datetime(2026, 8, 31, 8, 30)) is False  # not top of hour


def test_daily_due() -> None:
    role = role_named("planning")  # daily 08:00
    assert role is not None
    assert role_due(role, datetime(2026, 8, 31, 8, 0)) is True
    assert role_due(role, datetime(2026, 8, 31, 15, 0)) is False


def test_on_demand_never_auto() -> None:
    role = role_named("code")  # on demand
    assert role is not None
    assert role_due(role, datetime(2026, 8, 31, 12, 0)) is False


def test_due_roles_at_8am() -> None:
    due = {r.name for r in due_roles(datetime(2026, 8, 31, 8, 0))}
    # daily roles + every-2h/3h/6h that land on hour 8 + orchestrator 06/20? no
    assert "planning" in due
    assert "competitor-research" in due
    assert "social-media" in due  # every 2h, hour 8
    assert "orchestrator" not in due  # 06:00/20:00


def test_next_due_in() -> None:
    role = role_named("orchestrator")
    assert role is not None
    delta = next_due_in(role, datetime(2026, 8, 31, 7, 0))
    assert delta == timedelta(hours=13)  # next at 20:00
    delta2 = next_due_in(role, datetime(2026, 8, 31, 21, 0))
    assert delta2 == timedelta(hours=9)  # next day 06:00


def test_run_role_read_allows_draft() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())  # type: ignore[arg-type]
    result = agent.run_role("planning", objective="weekly plan")
    assert result.decision == "ALLOW"
    assert result.content == "role draft output"


def test_run_role_money_is_review() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())  # type: ignore[arg-type]
    result = agent.run_role("finance", objective="sync revenue")
    assert result.decision == "REVIEW"
    assert "approval" in result.summary


def test_run_role_social_is_review() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())  # type: ignore[arg-type]
    result = agent.run_role("social-media", objective="draft posts")
    assert result.decision == "REVIEW"


def test_run_role_unknown_denied() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())  # type: ignore[arg-type]
    result = agent.run_role("nope")
    assert result.decision == "DENY"


def test_role_dict_serializable() -> None:
    role = role_named("ads")
    assert role is not None
    d = role.as_dict()
    assert d["name"] == "ads"
    assert d["action_class"] == "commerce"
    assert d["cadence"] == "every 6h"
