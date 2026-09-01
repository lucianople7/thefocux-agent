"""Tests for the Expert Panel: playbooks + ask + quality review."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.experts import (  # noqa: E402
    _parse_review,
    ask_expert,
    list_experts,
    review_draft,
)
from runtime.memory import FocuxMemory  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402


def _gate() -> MoneyGate:
    return MoneyGate({
        ActionClass.READ: PolicyRule(ActionClass.READ, max_amount=0.0,
                                     auto_approve=True),
        ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
        ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
        ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
        ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
    })


class _EchoLLM:
    """Stub LLM: records the full prompt (system + user)."""

    def __init__(self) -> None:
        self.last_system = ""
        self.last_user = ""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.last_system = messages[0]["content"]
        self.last_user = messages[-1]["content"]
        return "expert answer with evidence"


class _ReviewLLM:
    """Stub LLM: returns a passing review JSON."""

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        return ('{"items": ['
                '{"item": "hook", "passed": true, "reason": "strong first line"}, '
                '{"item": "cta", "passed": true, "reason": "clear CTA"}, '
                '{"item": "evidence", "passed": true, "reason": "cites data"}, '
                '{"item": "format", "passed": false, "reason": "not native"}], '
                '"verdict": "PASS", "reason": "3 of 4 pass"}').replace(
                    '"verdict": "PASS"', '"verdict": "PASS"')


def _agent(mem: FocuxMemory | None, llm) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm, gate=_gate(), memory=mem, workspace="biz")  # type: ignore[arg-type]


# --- playbooks ---------------------------------------------------------------

def test_every_domain_has_playbook() -> None:
    experts = {e["domain"]: e for e in list_experts()}
    assert set(experts) == {"content", "social", "ecommerce",
                            "monetization", "opportunities"}
    for domain, meta in experts.items():
        assert meta["playbook"].endswith(f"{domain}.md")
        assert Path(meta["playbook"]).exists()
        text = Path(meta["playbook"]).read_text(encoding="utf-8")
        assert len(text) > 500  # real depth, not a stub


# --- ask ---------------------------------------------------------------------

def test_ask_expert_grounds_playbook_and_signals(tmp_path: Path) -> None:
    mem = FocuxMemory(tmp_path / "m.db")
    from runtime.ingest import SensorResult, store_results

    store_results({
        "github": SensorResult(
            source="github", ok=True,
            items=({"repo": "top/repo", "stars": 999, "language": "Python",
                    "description": "signal!"},),
            fetched_at="now"),
    }, mem, workspace="biz")
    llm = _EchoLLM()
    answer = ask_expert(_agent(mem, llm), "content",
                        "hook para un post sobre agentes", "biz")
    assert "world-class content strategist" in llm.last_system
    assert "## Your playbook" in llm.last_system  # playbook reached the expert
    assert "top/repo" in llm.last_user  # real signals reached the expert
    assert answer.decision == "ALLOW"  # read-class: gated allowed
    mem.close()


def test_ask_expert_unknown_domain() -> None:
    with pytest.raises(ValueError):
        ask_expert(_agent(None, _EchoLLM()), "nope", "q")


# --- review ------------------------------------------------------------------

def test_review_draft_thin_is_revise_without_judge(tmp_path: Path) -> None:
    verdict = review_draft(_agent(None, _EchoLLM()), "content", "corto")
    assert verdict.verdict == "REVISE"
    assert "too thin" in verdict.items[0].reason
    assert verdict.judge_reason == "deterministic pre-check"


def test_review_draft_judge_verdict(tmp_path: Path) -> None:
    draft = ("Los 5 errores que matan tu funnel (y como evitarlos) - "
             "datos de 200 campañas. Descarga la guia aqui.")
    verdict = review_draft(_agent(None, _ReviewLLM()), "content", draft)
    assert verdict.verdict == "PASS"
    assert len(verdict.items) == 4
    assert sum(1 for i in verdict.items if i.passed) >= 3
    assert verdict.judge_reason


def test_parse_review_unparseable() -> None:
    verdict = _parse_review("content", "no json here", "hook, cta")
    assert verdict.verdict == "REVISE"
    assert "unparseable" in verdict.judge_reason


def test_parse_review_math_is_honest() -> None:
    text = ('{"items": [{"item": "a", "passed": true, "reason": "r1"}, '
            '{"item": "b", "passed": false, "reason": "r2"}], '
            '"verdict": "REVISE", "reason": "only 1 of 2"}')
    verdict = _parse_review("content", text, "a, b")
    assert verdict.verdict == "REVISE"  # 50% < 60% threshold
    assert len(verdict.items) == 2
