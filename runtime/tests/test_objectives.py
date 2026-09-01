"""Tests for the Objective Brain: measurable goals + intelligence drive."""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.memory import FocuxMemory  # noqa: E402
from runtime.objectives import (  # noqa: E402
    DriveReport,
    _parse_plan,
    drive,
    format_drive,
    format_status,
    objective_status,
)
from runtime.agent import FocuxAgent  # noqa: E402
from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402


@pytest.fixture()
def mem(tmp_path: Path) -> FocuxMemory:
    m = FocuxMemory(tmp_path / "focux.db")
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


class _PlanLLM:
    """Stub LLM: returns a valid gated-plan JSON (research + content + money)."""

    def __init__(self) -> None:
        self.last_user = ""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.last_user = messages[-1]["content"]
        return (
            '[{"objective_id": "crecer-seguidores", '
            '"action": "analizar los repos con mas estrellas del nicho", '
            '"pillar": "research", "amount": 0}, '
            '{"objective_id": "crecer-seguidores", '
            '"action": "publicar 3 posts con los datos absorbidos", '
            '"pillar": "content", "amount": 0}, '
            '{"objective_id": "crecer-seguidores", '
            '"action": "comprar anuncios para 500 USD", '
            '"pillar": "monetization", "amount": 500}]'
        )


# --- store -------------------------------------------------------------------

def test_add_and_list_objective(mem: FocuxMemory) -> None:
    obj = mem.add_objective("biz", "Crecer seguidores", "followers", 1000,
                            unit="seguidores", deadline="2026-12-31")
    assert obj.objective_id == "crecer-seguidores"
    objs = mem.objectives("biz")
    assert len(objs) == 1
    assert objs[0].target == 1000
    assert objs[0].progress() == 0.0


def test_update_current_keeps_history(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Crecer seguidores", "followers", 1000)
    mem.update_objective_current("biz", "crecer-seguidores", 350)
    mem.update_objective_current("biz", "crecer-seguidores", 500)
    obj = mem.get_objective("biz", "crecer-seguidores")
    assert obj is not None and obj.current == 500
    assert obj.progress() == 0.5
    history = mem.objective_history("crecer-seguidores")
    assert [h[1] for h in history] == [350, 500]


def test_workspaces_isolate_objectives(mem: FocuxMemory) -> None:
    mem.add_objective("a", "Meta A", "k", 10)
    mem.add_objective("b", "Meta B", "k", 20)
    assert len(mem.objectives("a")) == 1
    assert mem.objectives("a")[0].title == "Meta A"


# --- status (deterministic math) --------------------------------------------

def test_status_progress_gap_overdue(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta A", "leads", 100, deadline="2020-01-01")
    mem.add_objective("biz", "Meta B", "leads", 100)
    mem.update_objective_current("biz", "meta-a", 40)
    statuses = objective_status(
        mem, "biz", now=datetime(2026, 1, 1, tzinfo=UTC), tier="high")
    by_id = {s.objective.objective_id: s for s in statuses}
    a = by_id["meta-a"]
    assert a.progress == 0.4
    assert a.gap == 60
    assert a.overdue is True  # deadline in the past, not achieved
    b = by_id["meta-b"]
    assert b.overdue is False
    assert b.tier == "high"


def test_status_achieved_and_delta(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta", "rev", 1000)
    mem.update_objective_current("biz", "meta", 600)
    mem.update_objective_current("biz", "meta", 1000)
    statuses = objective_status(mem, "biz")
    s = statuses[0]
    assert s.achieved is True
    assert s.delta == 400  # momentum: last measured jump


def test_status_empty(mem: FocuxMemory) -> None:
    assert objective_status(mem, "biz") == []


# --- drive (intelligence + gating) ------------------------------------------

def _agent(mem: FocuxMemory, llm: _PlanLLM) -> FocuxAgent:
    return FocuxAgent(llm=llm, gate=_gate(), memory=mem, workspace="biz")  # type: ignore[arg-type]


def test_drive_gates_proposals(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Crecer seguidores", "followers", 1000)
    llm = _PlanLLM()
    report = drive(_agent(mem, llm), "biz")
    assert report.note == ""
    by_pillar = {a["pillar"]: a for a in report.actions}
    assert by_pillar["research"]["decision"] == "ALLOW"  # read-class: can do
    assert by_pillar["content"]["decision"] == "REVIEW"  # publish: human
    assert by_pillar["monetization"]["decision"] == "REVIEW"  # money: never auto
    assert by_pillar["monetization"]["amount"] == 500
    # plan persisted on the objective
    obj = mem.get_objective("biz", "crecer-seguidores")
    assert obj is not None and len(obj.plan) == 3


def test_drive_injects_signals_into_prompt(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta", "k", 10)
    from runtime.ingest import SensorResult, store_results

    store_results({
        "github": SensorResult(
            source="github", ok=True,
            items=({"repo": "top/repo", "stars": 999, "language": "Python",
                    "description": "signal!"},),
            fetched_at="now"),
    }, mem, workspace="biz")
    llm = _PlanLLM()
    report = drive(_agent(mem, llm), "biz")
    assert "Absorbed signals (REAL data)" in llm.last_user
    assert "top/repo" in llm.last_user  # real data reaches the intelligence


def test_drive_no_objectives_honest(mem: FocuxMemory) -> None:
    report = drive(_agent(mem, _PlanLLM()), "biz")
    assert report.actions == []
    assert "no objectives" in report.note


def test_drive_unparseable_plan_honest(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta", "k", 10)

    class NoisyLLM:
        def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
            return "Lo siento, no puedo generar el plan."

    report = drive(_agent(mem, NoisyLLM()), "biz")  # type: ignore[arg-type]
    assert report.actions == []
    assert "could not parse" in report.note  # never an invented plan


def test_parse_plan_tolerant() -> None:
    text = 'Here is the plan:\n```json\n[{"objective_id": "a", "action": "x", "pillar": "research"}]\n```\n'
    plan = _parse_plan(text)
    assert len(plan) == 1
    assert plan[0]["action"] == "x"
    assert _parse_plan("no plan at all") == []
    assert _parse_plan('[{"action": "x", "pillar": "research"}]')[0][
        "objective_id"] == ""


# --- formatting --------------------------------------------------------------

def test_format_status_console_safe(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta con acentos y flecha \u2192", "k", 10)
    text = format_status(objective_status(mem, "biz"))
    text.encode("cp1252")  # must not raise


def test_format_drive_shape(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta", "k", 10)
    report = drive(_agent(mem, _PlanLLM()), "biz")
    text = format_drive(report)
    assert "DRIVE" in text
    assert "[ALLOW]" in text
    assert "[REVIEW]" in text
