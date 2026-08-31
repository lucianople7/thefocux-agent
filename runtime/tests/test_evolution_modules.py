"""Tests for daily evolution + modular system."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from runtime.evolution import (  # noqa: E402
    EvolutionProposal,
    analyze,
    format_report,
    run_daily_evolution,
)
from runtime.modules import all_modules, integrity_check, module_named  # noqa: E402
from runtime.orchestrator import all_roles, role_named  # noqa: E402


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
        return "stub"


# --- evolution ---------------------------------------------------------------

def test_analyze_flags_failure_heavy(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(tmp_path / "m.db")
    mem.learn_procedure("biz", "broken-flow", ("a", "b"))
    mem.record_outcome("biz", "broken-flow", success=False)
    mem.record_outcome("biz", "broken-flow", success=False)
    mem.record_outcome("biz", "broken-flow", success=True)
    report = analyze(mem, "biz")
    kinds = [p.kind for p in report.proposals]
    assert "fix" in kinds
    fix = next(p for p in report.proposals if p.kind == "fix")
    assert fix.target == "broken-flow"
    assert "2 fail" in fix.evidence
    mem.close()


def test_analyze_crystallizes_winner(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(tmp_path / "m.db")
    mem.learn_procedure("biz", "winning-flow", ("a", "b"))
    for _ in range(4):
        mem.record_outcome("biz", "winning-flow", success=True)
    report = analyze(mem, "biz")
    kinds = [p.kind for p in report.proposals]
    assert "crystallize" in kinds
    win = next(p for p in report.proposals if p.kind == "crystallize")
    assert win.target == "winning-flow"
    mem.close()


def test_analyze_lists_drafts(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory
    from runtime.skills import crystallize_skill

    drafts = tmp_path / "skills-draft"
    crystallize_skill(drafts, name="pending-draft", description="x", body="b")
    mem = FocuxMemory(tmp_path / "m.db")
    report = analyze(mem, "biz", drafts_dir=drafts)
    assert any(p.kind == "promote" and p.target == "pending-draft"
               for p in report.proposals)
    mem.close()


def test_run_daily_evolution_records_event(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(tmp_path / "focux.db")
    mem.learn_procedure("biz", "flow", ("x",))
    mem.record_outcome("biz", "flow", success=False)
    mem.record_outcome("biz", "flow", success=False)
    mem.close()

    report = run_daily_evolution(
        workspace="biz", memory_dir=tmp_path, drafts_dir=tmp_path / "sd"
    )
    assert "procedures analyzed" in report.summary

    mem2 = FocuxMemory(tmp_path / "focux.db")
    events = mem2.recent_events("biz")
    assert any(e.kind == "evolution" for e in events)
    mem2.close()


def test_format_report(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory

    mem = FocuxMemory(tmp_path / "m.db")
    report = analyze(mem, "biz")
    mem.close()
    text = format_report(report)
    assert "EVOLUTION" in text
    assert "procedures analyzed" in text


def test_evolution_role_in_orchestrator() -> None:
    role = role_named("evolution")
    assert role is not None
    assert role.cadence == "daily"
    assert role.pillar == "research"
    names = {r.name for r in all_roles()}
    assert "evolution" in names
    assert len(names) == 10


def test_run_role_evolution(tmp_path: Path) -> None:
    from runtime.memory import FocuxMemory

    # seed memory with a failure-heavy procedure via the agent's workspace
    mem = FocuxMemory(tmp_path / "focux.db")
    mem.learn_procedure("biz", "flow", ("x",))
    mem.record_outcome("biz", "flow", success=False)
    mem.record_outcome("biz", "flow", success=False)
    mem.close()

    agent = FocuxAgent(
        llm=_StubLLM(),  # type: ignore[arg-type]
        gate=_gate(),
        memory=FocuxMemory(tmp_path / "focux.db"),
        workspace="biz",
        drafts_dir=tmp_path / "sd",
    )
    result = agent.run_role("evolution")
    assert result.decision == "ALLOW"
    assert "EVOLUTION" in result.content
    assert "fix" in result.content


# --- modules -----------------------------------------------------------------

def test_all_modules_registered() -> None:
    modules = all_modules()
    ids = {m.id for m in modules}
    assert {"money-gate", "memory", "survival", "heartbeat", "selfmod",
            "orchestrator", "evolution", "tools", "eval", "mcp-bridge",
            "webui"} <= ids


def test_module_versions_semver() -> None:
    import re

    for module in all_modules():
        assert re.fullmatch(r"\d+\.\d+\.\d+", module.version), module.id


def test_integrity_check_all_ok() -> None:
    check = integrity_check()
    assert check["ok"] is True, check["modules"]
    assert check["count"] >= len(all_modules()) + 1  # + falsification


def test_module_named() -> None:
    assert module_named("survival") is not None
    assert module_named("nope") is None


def test_modules_deps_are_registered() -> None:
    ids = {m.id for m in all_modules()}
    for module in all_modules():
        for dep in module.deps:
            assert dep in ids, f"{module.id} depends on unknown {dep}"
