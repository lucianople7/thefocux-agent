"""Tests for the Work Harness: durable stage-gated work (Automaton mindset)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.workflow import (  # noqa: E402
    STAGES,
    WorkState,
    _parse_steps,
    approve,
    execute,
    frame,
    load_state,
    plan,
    resume_text,
    status_text,
    validate,
    verify,
    work_root,
)
from runtime.memory import FocuxMemory  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    return tmp_path / "project"


def _gate() -> MoneyGate:
    return MoneyGate({
        ActionClass.READ: PolicyRule(ActionClass.READ, max_amount=0.0,
                                     auto_approve=True),
        ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
        ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
        ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
        ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
    })


class _SpecLLM:
    def __init__(self) -> None:
        self.last_user = ""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.last_user = messages[-1]["content"]
        return ("## Objective\nBuild X\n## Success criteria\n1. it works\n"
                "## Constraints\nnone")


class _PlanLLM:
    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        return ("# PLAN\n## Steps\n"
                "1. analyze the niche [pillar: research]\n"
                "2. publish the post [pillar: content]\n"
                "3. charge 500 USD [pillar: monetization]\n"
                "## Verification\n- tests pass")


class _ContentVerifyLLM:
    """Content-domain verify: expert review returns PASS."""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        user = messages[-1]["content"]
        if "quality judge" in messages[0]["content"] or "judge" in messages[0]["content"]:
            return ('{"items": [{"item": "hook", "passed": true, "reason": "ok"}, '
                    '{"item": "cta", "passed": true, "reason": "ok"}, '
                    '{"item": "evidence", "passed": true, "reason": "ok"}, '
                    '{"item": "format", "passed": true, "reason": "ok"}], '
                    '"verdict": "PASS", "reason": "all pass"}')
        return "SPEC body"


def _agent(llm, mem: FocuxMemory | None = None) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm, gate=_gate(), memory=mem, workspace="biz")  # type: ignore[arg-type]


# --- frame + state -----------------------------------------------------------

def test_frame_writes_spec_and_state(project: Path) -> None:
    state = frame(_agent(_SpecLLM()), "Build the landing",
                  cwd=project, workspace="biz")
    assert state.stage == "framed"
    assert state.spec_path.exists()
    assert (project / ".focux" / "work" / "current.json").exists()
    assert "Success criteria" in state.spec_path.read_text(encoding="utf-8")
    loaded = load_state(state.root)
    assert loaded is not None and loaded.objective == "Build the landing"


def test_frame_blocks_active_work(project: Path) -> None:
    frame(_agent(_SpecLLM()), "First", cwd=project)
    with pytest.raises(ValueError):
        frame(_agent(_SpecLLM()), "Second", cwd=project)
    # --force replaces
    state = frame(_agent(_SpecLLM()), "Second", cwd=project, force=True)
    assert state.objective == "Second"


# --- stage machine -----------------------------------------------------------

def test_full_stage_machine_code(project: Path) -> None:
    project.mkdir(parents=True)
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    state = frame(_agent(_SpecLLM()), "Ship it", domain="code", cwd=project)
    state = approve(state)
    assert state.stage == "framed"  # approval keeps frame stage (review done)
    assert "approved" in state.history[-1]
    state = plan(_agent(_PlanLLM()), state)
    assert state.stage == "planned"
    assert state.plan_path.exists()
    # execute gates each step
    gated = execute(_agent(_PlanLLM()), state)
    by_pillar = {g["pillar"]: g["decision"] for g in gated}
    assert by_pillar["research"] == "ALLOW"
    assert by_pillar["content"] == "REVIEW"
    assert by_pillar["monetization"] == "REVIEW"
    assert state.stage == "executing"
    # verify runs the project's pytest (no tests collected -> fails honestly)
    state = verify(_agent(_PlanLLM()), state)
    assert state.stage == "executing"  # not verified
    assert any("pytest=" in h for h in state.history)


def test_full_stage_machine_content_verified(project: Path) -> None:
    llm = _ContentVerifyLLM()
    state = frame(_agent(llm), "Write the guide", domain="content", cwd=project)
    state = approve(state)
    state = plan(_agent(llm), state)
    state = verify(_agent(llm), state)
    assert state.stage == "verified"  # terminal
    assert state.roadmap_path.exists()
    # verified is durable across "sessions"
    loaded = load_state(state.root)
    assert loaded is not None and loaded.stage == "verified"


def test_verify_confirm_without_checks(project: Path) -> None:
    state = frame(_agent(_SpecLLM()), "No tests here", domain="code", cwd=project)
    state = plan(_agent(_PlanLLM()), state)
    state = verify(_agent(_PlanLLM()), state, confirm=True)
    assert state.stage == "verified"
    assert any("human confirmation" in h for h in state.history)


# --- session-start honesty ---------------------------------------------------

def test_status_no_work_says_do_it_directly(project: Path) -> None:
    text = status_text(work_root(project))
    assert "DO IT DIRECTLY" in text
    assert "frame" in text


def test_status_verified_is_quiet(project: Path) -> None:
    state = frame(_agent(_ContentVerifyLLM()), "Done work", domain="content",
                  cwd=project)
    state = verify(_agent(_ContentVerifyLLM()), state)  # PASS -> verified
    assert state.stage == "verified"
    text = status_text(state.root)
    assert "Quiet" in text
    assert "disengaged" in text


def test_resume_prints_next_step(project: Path) -> None:
    state = frame(_agent(_SpecLLM()), "Resume me", cwd=project)
    text = resume_text(state.root)
    assert "RESUME" in text
    assert "focux work approve" in text  # framed -> next step


# --- parse + validate --------------------------------------------------------

def test_parse_steps_from_plan() -> None:
    plan_file = Path(__file__).parent / "_plan_sample.md"
    plan_file.write_text(
        "# PLAN\n1. do research [pillar: research]\n"
        "2. publish [pillar: content]\n3. no pillar here\n", encoding="utf-8")
    steps = _parse_steps(plan_file)
    assert len(steps) == 2
    assert steps[0] == {"action": "do research", "pillar": "research"}
    plan_file.unlink()


def test_validate_consistency(project: Path) -> None:
    root = work_root(project)
    issues = validate(root)
    assert issues == ["no .focux/work state in this project"]
    frame(_agent(_SpecLLM()), "Check me", cwd=project)
    assert validate(root) == []
    # break it: delete SPEC.md
    (root / "SPEC.md").unlink()
    assert "SPEC.md missing" in validate(root)
