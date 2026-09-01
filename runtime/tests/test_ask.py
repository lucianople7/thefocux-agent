"""Tests for the universal brain interface: ask + insights (anything CLI)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.ask import AskResult, _parse_insights, ask, insights  # noqa: E402
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


class _AskLLM:
    def __init__(self) -> None:
        self.last_user = ""
        self.last_system = ""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.last_user = messages[-1]["content"]
        self.last_system = messages[0]["content"]
        return "answer with evidence"


class _InsightsLLM:
    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        return ('[{"insight": "publicar guia de agentes", "pillar": "content", '
                '"why": "los datos muestran demanda"}, '
                '{"insight": "cobrar 500 USD", "pillar": "monetization", '
                '"why": "oferta lista"}]')


def _agent(mem: FocuxMemory | None, llm) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm, gate=_gate(), memory=mem, workspace="biz")  # type: ignore[arg-type]


def test_ask_is_gated_and_directed(mem: FocuxMemory) -> None:
    from runtime.ingest import SensorResult, store_results

    mem.add_objective("biz", "Crecer seguidores", "followers", 1000)
    store_results({
        "github": SensorResult(
            source="github", ok=True,
            items=({"repo": "top/repo", "stars": 999, "language": "Python",
                    "description": "signal!"},),
            fetched_at="now"),
    }, mem, workspace="biz")
    llm = _AskLLM()
    result = ask(_agent(mem, llm), "que hacemos esta semana?", "biz")
    assert result.decision == "ALLOW"  # read-class
    assert result.answer == "answer with evidence"
    # the question reached the brain WITH directed context
    assert "que hacemos esta semana?" in llm.last_user
    assert "Crecer seguidores" in llm.last_user  # real goals in context
    assert "top/repo" in llm.last_user  # real signals in context
    assert "real goals" in llm.last_system


def test_insights_gated(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Crecer", "followers", 1000)
    report = insights(_agent(mem, _InsightsLLM()), "biz", limit=2)
    by_pillar = {i["pillar"]: i["decision"] for i in report["insights"]}
    assert by_pillar["content"] == "REVIEW"  # publishing needs human
    assert by_pillar["monetization"] == "REVIEW"  # money never auto
    assert len(report["insights"]) == 2


def test_insights_parse_tolerant() -> None:
    assert _parse_insights('[{"insight": "x", "pillar": "research"}]') == [
        {"insight": "x", "pillar": "research", "why": ""}]
    assert _parse_insights("no json") == []
    fenced = '```json\n[{"insight": "y", "pillar": "content"}]\n```'
    assert _parse_insights(fenced)[0]["insight"] == "y"


def test_ask_no_memory_honest() -> None:
    llm = _AskLLM()
    result = ask(_agent(None, llm), "hola", "biz")
    assert result.decision == "ALLOW"
    assert result.answer
