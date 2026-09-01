"""Tests for THE FOCUX FOCUS: directed intelligence for ANY agent."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.focus import (  # noqa: E402
    FOCUS_FILE,
    focus_pack,
    format_focus,
    write_focus_file,
)
from runtime.memory import FocuxMemory  # noqa: E402


@pytest.fixture()
def mem(tmp_path: Path) -> FocuxMemory:
    m = FocuxMemory(tmp_path / "m.db")
    yield m
    m.close()


def test_focus_pack_contains_goals_and_evidence(mem: FocuxMemory) -> None:
    from runtime.ingest import SensorResult, store_results

    mem.add_objective("biz", "Crecer seguidores", "followers", 1000)
    mem.update_objective_current("biz", "crecer-seguidores", 400)
    store_results({
        "github": SensorResult(
            source="github", ok=True,
            items=({"repo": "top/repo", "stars": 999, "language": "Python",
                    "description": "signal!"},),
            fetched_at="now"),
    }, mem, workspace="biz")
    pack = focus_pack(mem, "biz", tier="low_compute")
    assert len(pack.objectives) == 1
    obj = pack.objectives[0]
    assert obj["objective_id"] == "crecer-seguidores"
    assert obj["progress"] == 0.4
    assert obj["gap"] == 600
    assert pack.signals[0].startswith("github: top/repo (999 stars, Python)")
    assert pack.tier == "low_compute"


def test_focus_no_goals_is_honest(mem: FocuxMemory) -> None:
    pack = focus_pack(mem, "biz")
    assert pack.objectives == ()
    text = format_focus(pack)
    assert "none set" in text
    assert "intelligence without goals is noise" in text


def test_focus_format_is_console_safe(mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta con acentos \u00e1\u00e9\u00ed", "k", 10)
    text = format_focus(focus_pack(mem, "biz"))
    text.encode("cp1252")  # must not raise


def test_focus_includes_work_state(tmp_path: Path) -> None:
    from runtime.workflow import frame
    from runtime.agent import FocuxAgent  # noqa: F401
    from policy.money_gate import ActionClass, MoneyGate, PolicyRule

    project = tmp_path / "project"

    class StubLLM:
        def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
            return "## Success criteria\n1. works"

    gate = MoneyGate({ActionClass.READ: PolicyRule(
        ActionClass.READ, max_amount=0.0, auto_approve=True)})
    agent = FocuxAgent(llm=StubLLM(), gate=gate, memory=None, workspace="biz")  # type: ignore[arg-type]
    frame(agent, "Ship the landing", cwd=project)
    pack = focus_pack(None, "biz", cwd=project)
    assert "SPEC.md awaits YOUR review" in pack.work
    text = format_focus(pack)
    assert "Estado del trabajo" in text


def test_write_focus_file(tmp_path: Path, mem: FocuxMemory) -> None:
    mem.add_objective("biz", "Meta", "k", 10)
    path = write_focus_file(focus_pack(mem, "biz"), cwd=tmp_path)
    assert path == tmp_path / ".focux" / FOCUS_FILE
    text = path.read_text(encoding="utf-8")
    assert "# THE FOCUX FOCUS" in text
    assert "Meta" in text
