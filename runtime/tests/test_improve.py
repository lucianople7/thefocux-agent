"""Tests for the SUCCESS GOVERNOR: improvements at all hours (gated)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.improve import _parse, format_improve, improve  # noqa: E402
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
        ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
        ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
        ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
    })


class _ImproveLLM:
    def __init__(self) -> None:
        self.last_user = ""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.last_user = messages[-1]["content"]
        return ('[{"improvement": "publicar la pieza 3 con los datos absorbidos", '
                '"target": "business", "pillar": "content", '
                '"metric": "2/3 -> 3/3 piezas", "why": "gap 1 y evidencia lista"}, '
                '{"improvement": "automatizar la reconstruccion del mapa en daily", '
                '"target": "system", "pillar": "research", '
                '"metric": "mapa stale -> siempre fresco", "why": "el daily ya corre"}]')


def _agent(mem: FocuxMemory, llm=None) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm or _ImproveLLM(), gate=_gate(), memory=mem,
                      workspace="biz")  # type: ignore[arg-type]


def test_improve_uses_evidence_and_gates(mem: FocuxMemory) -> None:
    from runtime.lessons import save_lesson

    mem.add_objective("biz", "Publicar piezas", "piezas", 3)
    mem.update_objective_current("biz", "publicar-piezas", 2)
    save_lesson(mem, "biz", "Los datos reales ganan")
    llm = _ImproveLLM()
    report = improve(_agent(mem, llm), "biz", limit=2)
    assert len(report["improvements"]) == 2
    by_target = {i["target"]: i["decision"] for i in report["improvements"]}
    assert by_target["business"] == "REVIEW"  # publishing: human
    assert by_target["system"] == "ALLOW"  # research/read: can do
    # evidence reached the governor
    assert "Publicar piezas" in llm.last_user
    assert "Los datos reales ganan" in llm.last_user
    # proposals stored as improve events (next cycle sees them)
    kinds = {e.kind for e in mem.recent_events("biz", limit=10)}
    assert "improve" in kinds


def test_improve_parse_tolerant() -> None:
    assert _parse('[{"improvement": "x", "target": "system"}]')[0][
        "target"] == "system"
    assert _parse("no json") == []


def test_format_improve_console_safe() -> None:
    report = {"improvements": [
        {"decision": "REVIEW", "target": "business", "pillar": "content",
         "improvement": "mejora con acentos \u00e1", "metric": "1 -> 2",
         "why": "evidencia"}]}
    text = format_improve(report)
    text.encode("cp1252")  # must not raise
    assert "IMPROVE" in text


def test_improve_empty_honest(mem: FocuxMemory) -> None:
    class Noisy:
        def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
            return "no puedo generar mejoras"

    report = improve(_agent(mem, Noisy()), "biz")  # type: ignore[arg-type]
    assert report["improvements"] == []
    assert "nothing invented" in format_improve(report)
