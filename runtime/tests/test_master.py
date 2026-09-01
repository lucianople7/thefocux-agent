"""Tests for THE FOCUX MASTER: one-glance status + the daily cycle."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.master import (  # noqa: E402
    daily_cycle,
    format_daily,
    format_master_status,
    master_status,
)
from runtime.memory import FocuxMemory  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402


@pytest.fixture()
def mem(tmp_path: Path) -> FocuxMemory:
    m = FocuxMemory(tmp_path / "m.db")
    yield m
    m.close()


def _gate() -> MoneyGate:
    return MoneyGate({
        ActionClass.READ: PolicyRule(ActionClass.READ, max_amount=0.0,
                                     auto_approve=True),
        ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
        ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
        ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
        ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
    })


class _DailyLLM:
    """Stub: returns a gated-plan JSON for drive and insights prompts."""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        user = messages[-1]["content"]
        if "propose exactly" in user and "opportunities" in user:
            # insights: opportunity shape
            return ('[{"insight": "guia de agentes", "pillar": "content", '
                    '"why": "demanda real"}, '
                    '{"insight": "cobrar por la guia", "pillar": "monetization", '
                    '"why": "oferta lista"}]')
        # drive: objective action shape
        return ('[{"objective_id": "meta-a", "action": "publicar la guia", '
                '"pillar": "content"}, '
                '{"objective_id": "meta-a", "action": "cobrar 500 USD", '
                '"pillar": "monetization", "amount": 500}]')


def _agent(mem: FocuxMemory, llm=None) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm or _DailyLLM(), gate=_gate(), memory=mem,
                      workspace="biz")  # type: ignore[arg-type]


def test_master_status_shape(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta A", "leads", 100)
    mem.update_objective_current("biz", "meta-a", 40)
    data = master_status(mem, "biz", revenue=1000, operating_cost=2000,
                         cash=500)
    assert data["tier"] in ("high", "normal", "low_compute", "critical", "dead")
    assert len(data["objectives"]) == 1
    assert data["objectives"][0]["progress"] == 0.4
    assert data["work"]["stage"] is None
    assert data["absorb"]["fresh"] is False
    assert "mcp" in data
    text = format_master_status(data)
    text.encode("cp1252")  # console-safe


def test_daily_cycle_full(mem: FocuxMemory, tmp_path: Path) -> None:
    mem.add_objective("biz", "Meta A", "leads", 100)
    agent = _agent(mem)
    report = daily_cycle(agent, "biz", revenue=1000, operating_cost=2000,
                         cash=500, sources=(), limit=2, cwd=tmp_path)
    assert report["tier"]
    assert report["absorbed"]["stored"] == 0  # no network sources
    assert report["focus"]["file"].endswith("focus.md")
    # drive actions gated: content + monetization both REVIEW
    drive_pillars = {a["pillar"]: a["decision"] for a in report["drive"]["actions"]}
    assert drive_pillars["content"] == "REVIEW"
    assert drive_pillars["monetization"] == "REVIEW"
    # insights gated the same way
    insight_pillars = {i["pillar"]: i["decision"]
                       for i in report["insights"]["insights"]}
    assert insight_pillars["monetization"] == "REVIEW"
    # heartbeat present with tier
    assert report["heartbeat"]["tier"]
    # the whole thing formats for humans, console-safe
    text = format_daily(report)
    text.encode("cp1252")
    assert "DAILY CYCLE" in text
    assert "REVIEW" in text


def test_daily_cycle_without_memory_honest(tmp_path: Path) -> None:
    agent = FocuxAgent(llm=_DailyLLM(), gate=_gate(), memory=None,
                       workspace="biz")  # type: ignore[arg-type]
    report = daily_cycle(agent, "biz", sources=(), cwd=tmp_path)
    assert report["absorbed"]["stored"] == 0
    assert report["focus"]["objectives"] == []
