"""Tests for the FOCUX BRAIN — survival tiers, self-mod audit, heartbeat."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from runtime.heartbeat import format_report, heartbeat  # noqa: E402
from runtime.selfmod import RateLimiter, SelfModLog, is_protected  # noqa: E402
from runtime.survival import (  # noqa: E402
    BusinessFinances,
    SurvivalTier,
    report,
    survival_tier,
    tier_behavior,
)


# --- survival ---------------------------------------------------------------

def test_tier_high_runway() -> None:
    f = BusinessFinances(revenue=10000, operating_cost=1000, cash=30000)
    assert survival_tier(f) is SurvivalTier.HIGH  # 30d+ runway


def test_tier_normal() -> None:
    f = BusinessFinances(revenue=1000, operating_cost=900, cash=3000)
    # daily burn 30, buffer 3000+100 = 3100 -> ~103 days? no: profit 100, cash 3000
    # runway = (3000 + 100) / (900/30) = 3100/30 = 103d -> HIGH. Use cost closer.
    f2 = BusinessFinances(revenue=1000, operating_cost=950, cash=1000)
    # (1000+50)/(950/30)=1050/31.7=33d -> NORMAL
    assert survival_tier(f2) is SurvivalTier.NORMAL


def test_tier_critical_when_broke() -> None:
    f = BusinessFinances(revenue=100, operating_cost=200, cash=0)
    # profit -100, runway = (0 + 0)/... daily=6.67 -> (0+max(0,-100))/6.67=0 -> CRITICAL
    assert survival_tier(f) is SurvivalTier.CRITICAL


def test_tier_dead_when_negative() -> None:
    f = BusinessFinances(revenue=0, operating_cost=100, cash=-500)
    # profit -100, runway = (-500 + 0)/(100/30) = -500/3.33 = -150 -> DEAD
    assert survival_tier(f) is SurvivalTier.DEAD


def test_tier_zero_cost_is_high() -> None:
    f = BusinessFinances(revenue=0, operating_cost=0, cash=0)
    assert survival_tier(f) is SurvivalTier.HIGH  # infinite runway


def test_tiers_change_effort_not_authorization() -> None:
    for tier in SurvivalTier:
        behavior = tier_behavior(tier)
        assert "model" in behavior
        assert "heartbeat" in behavior
        # No tier may contain an authorization field.
        assert "authorization" not in behavior


def test_survival_report() -> None:
    f = BusinessFinances(revenue=1000, operating_cost=900, cash=5000)
    r = report(f)
    assert "tier" in r
    assert r["authorization_unchanged"] is True


# --- self-mod ---------------------------------------------------------------

def test_selfmod_append_only(tmp_path: Path) -> None:
    log = SelfModLog(tmp_path / "selfmod.jsonl")
    log.append("skill_crystallized", "newsletter-draft")
    log.append("procedure_learned", "metrics")
    entries = log.entries()
    assert len(entries) == 2
    assert entries[0].kind == "skill_crystallized"
    assert log.count("skill_crystallized") == 1


def test_selfmod_handles_non_serializable_data(tmp_path: Path) -> None:
    """REGRESSION (round 1): audit must never break on weird data."""
    log = SelfModLog(tmp_path / "selfmod.jsonl")
    entry = log.append("skill_crystallized", "weird", data={"obj": object()})
    # entry readable back, non-serializable degraded
    entries = log.entries()
    assert len(entries) == 1
    assert "non-serializable" in entries[0].data["obj"]
    assert entry.id == entries[0].id


def test_selfmod_parallel_appends_no_loss(tmp_path: Path) -> None:
    """REGRESSION (round 5): parallel appends must not lose entries."""
    import threading

    log = SelfModLog(tmp_path / "selfmod.jsonl")
    errors: list[Exception] = []

    def writer(k: int) -> None:
        try:
            for i in range(50):
                log.append("kind", f"{k}-{i}", data={"n": i})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(k,)) for k in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    assert len(log.entries(limit=10_000)) == 8 * 50


def test_selfmod_persists(tmp_path: Path) -> None:
    path = tmp_path / "selfmod.jsonl"
    log1 = SelfModLog(path)
    log1.append("draft_promoted", "x")
    log2 = SelfModLog(path)
    assert log2.count() == 1


def test_rate_limiter() -> None:
    lim = RateLimiter(window_seconds=3600, max_ops=3)
    assert lim.allow(100.0)
    assert lim.allow(101.0)
    assert lim.allow(102.0)
    assert not lim.allow(103.0)  # blocked
    assert lim.remaining == 0
    # window slides
    assert lim.allow(3600 + 200.0)  # old times expired


def test_protected_paths() -> None:
    assert is_protected("constitution.md")
    assert is_protected("policy/money_gate.py")
    assert not is_protected("skills/my-skill")


def test_learn_is_audited(tmp_path: Path) -> None:
    agent = FocuxAgent(
        llm=_StubLLM(),  # type: ignore[arg-type]
        gate=_gate(),
        drafts_dir=tmp_path / "skills-draft",
    )
    agent.learn("audited-skill", ("a", "b"), description="audited")
    log = SelfModLog()  # default path memory/selfmod.jsonl
    kinds = [e.kind for e in log.entries()]
    assert any(k == "skill_crystallized" for k in kinds)


def test_learn_protected_denied(tmp_path: Path) -> None:
    agent = FocuxAgent(
        llm=_StubLLM(),  # type: ignore[arg-type]
        gate=_gate(),
        drafts_dir=tmp_path / "skills-draft",
    )
    result = agent.learn("constitution.md", ("a",))
    assert result["learned"] is False
    assert "protected" in result["reason"]


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


# --- heartbeat --------------------------------------------------------------

def test_heartbeat_report_shape() -> None:
    f = BusinessFinances(revenue=1000, operating_cost=900, cash=1000)
    hb = heartbeat(f, now=datetime(2026, 8, 31, 8, 0, tzinfo=timezone.utc))
    assert hb.tier == "normal" or hb.tier == "high" or hb.tier == "low_compute"
    assert "roles_due" in hb.as_dict()
    assert "roles_next_minutes" in hb.as_dict()
    assert "pending_approvals" in hb.as_dict()


def test_heartbeat_healthy_flag() -> None:
    f = BusinessFinances(revenue=5000, operating_cost=500, cash=20000)
    hb = heartbeat(f)
    assert hb.healthy is True
    dead = BusinessFinances(revenue=0, operating_cost=100, cash=-100)
    hb2 = heartbeat(dead)
    assert hb2.healthy is False


def test_format_report() -> None:
    f = BusinessFinances(revenue=1000, operating_cost=900, cash=1000)
    hb = heartbeat(f)
    text = format_report(hb)
    assert "HEARTBEAT" in text
    assert "Tier:" in text
