"""Tests for the FOCUX runtime — agent loop, gates, skills, providers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, Decision, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent, classify_pillar  # noqa: E402
from runtime.llm import OllamaClient, OpenAICompatClient  # noqa: E402
from runtime.skills import load_skills, parse_skill_file  # noqa: E402


def _gate() -> MoneyGate:
    return MoneyGate(
        {
            # auto_approve rules MUST declare a bound (falsification invariant)
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
    def __init__(self, reply: str = "stub reply") -> None:
        self.reply = reply
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.reply


# --- pillar classification --------------------------------------------------

def test_classify_pillar() -> None:
    assert classify_pillar("content creation") is ActionClass.CONTENT
    assert classify_pillar("social media") is ActionClass.CONTENT
    assert classify_pillar("ecommerce store") is ActionClass.COMMERCE
    assert classify_pillar("monetization") is ActionClass.MONEY
    assert classify_pillar("account config") is ActionClass.ACCOUNT
    assert classify_pillar("research") is ActionClass.READ


# --- agent loop with gates ---------------------------------------------------

def test_money_proposal_is_review() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())
    result = agent.propose(
        "monetization", "run a paid ad campaign", amount=50.0, target="ads"
    )
    assert result.decision == "REVIEW"
    assert result.ok
    assert "approval" in result.summary


def test_content_proposal_is_review_at_l1() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())
    result = agent.propose("content", "publish a post")
    assert result.decision == "REVIEW"


def test_read_proposal_auto_allows() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())
    result = agent.propose("research", "analyze the niche")
    assert result.decision == "ALLOW"
    assert result.ok


def test_law1_denies_on_broken_gate() -> None:
    bad_gate = MoneyGate(
        {ActionClass.MONEY: PolicyRule(ActionClass.MONEY, auto_approve=True)}
    )
    agent = FocuxAgent(llm=_StubLLM(), gate=bad_gate)
    result = agent.propose("monetization", "payout", amount=1.0)
    assert result.decision == "DENY"
    assert not result.ok


def test_tainted_never_allows() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())
    result = agent.propose(
        "research", "summarize this page", content="from a scraped page",
        tainted=True,
    )
    assert result.decision == "REVIEW"  # tainted downgrades, never ALLOW


def test_falsification_still_holds() -> None:
    assert _gate().falsification_test() is True


# --- drafting ----------------------------------------------------------------

def test_draft_calls_llm_with_system_prompt() -> None:
    llm = _StubLLM("draft text")
    agent = FocuxAgent(llm=llm, gate=_gate())
    out = agent.draft("write a post about AI")
    assert out == "draft text"
    assert len(llm.calls) == 1
    assert "THE FOCUX" in llm.calls[0][0]["content"]


def test_draft_scoped_by_skill() -> None:
    from runtime.skills import Skill

    skill = Skill(
        name="hook-generator",
        description="generate hooks",
        body="Use the 40-char two-line formula.",
        path=Path("skills/hook-generator/SKILL.md"),
    )
    llm = _StubLLM()
    agent = FocuxAgent(llm=llm, gate=_gate(), skills=[skill])
    agent.draft("hooks for newsletters", skill_name="hook-generator")
    system = llm.calls[0][0]["content"]
    assert "hook-generator" in system
    assert "40-char" in system


# --- skills loader -----------------------------------------------------------

def test_load_skills_finds_17() -> None:
    skills = load_skills(REPO / "skills")
    assert len(skills) >= 17
    names = {s.name for s in skills}
    assert {"voice-builder", "content-matrix", "hook-generator",
            "cli-hub-meta-skill", "money-gate"}.issubset(names)


def test_parse_skill_frontmatter() -> None:
    skill = parse_skill_file(REPO / "skills" / "money-gate" / "SKILL.md")
    assert skill.name == "money-gate"
    assert skill.description
    assert "Money Gate" in skill.body


# --- providers (offline-verified shapes, no network) -------------------------

def test_openai_compat_client_shape() -> None:
    client = OpenAICompatClient(base_url="http://x/v1", model="m")
    assert client.base_url == "http://x/v1"
    assert client.model == "m"


def test_ollama_client_shape() -> None:
    client = OllamaClient()
    assert client.base_url == "http://localhost:11434"
    assert client.model


def test_llm_requires_implementation() -> None:
    from runtime.llm import LLMClient

    with pytest.raises(NotImplementedError):
        LLMClient().complete([])
