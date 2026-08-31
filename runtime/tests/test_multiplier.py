"""Tests for the revenue multiplier: content multiplier + offer ladder."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402
from runtime.agent import FocuxAgent  # noqa: E402
from runtime.offer import build_ladder, format_ladder  # noqa: E402
from runtime.orchestrator import all_roles, role_named  # noqa: E402
from runtime.repurpose import (  # noqa: E402
    MultipliedAsset,
    format_plan,
    multiply,
    multiplier_plan,
    write_asset,
)


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
        return "drafted output"


# --- multiplier --------------------------------------------------------------

def test_multiplier_plan_has_20_outputs() -> None:
    assets = multiplier_plan()
    assert len(assets) == 20
    ids = {a.id for a in assets}
    assert {"linkedin-post", "x-thread", "instagram-carousel", "youtube-script",
            "newsletter-blurb", "email-tip", "quote-post", "tiktok-script"} <= ids
    # all platforms covered
    platforms = {a.platform for a in assets}
    assert len(platforms) >= 8


def test_multiplier_gate_blocks_extraction() -> None:
    assets = multiply(
        "get rich quick by clicking here now",
        offer="",
    )
    # The multiplier still returns 20 assets but those failing Law II are flagged.
    assert len(assets) == 20
    assert any(not a.passed_gate for a in assets)


def test_write_asset_with_llm() -> None:
    asset = multiplier_plan()[0]
    written = write_asset(
        asset,
        "A clear honest insight about X",
        offer="free guide",
        write=lambda a, i, o: f"draft for {a.id}",
    )
    assert written.draft == "draft for linkedin-post"
    assert written.passed_gate is True


def test_multiply_with_writer() -> None:
    assets = multiply(
        "A clear honest insight about X",
        offer="free guide",
        write=lambda a, i, o: f"[{a.id}] draft",
    )
    assert len(assets) == 20
    assert all(a.draft for a in assets)


def test_format_plan() -> None:
    assets = multiplier_plan()
    text = format_plan(assets)
    assert "CONTENT MULTIPLIER" in text
    assert "20 outputs" in text
    assert "20 passed the gate" in text


def test_assets_serializable() -> None:
    asset = multiplier_plan()[0]
    d = asset.as_dict()
    assert set(d) == {"id", "platform", "format", "brief", "cta", "draft"}


# --- offer ladder ------------------------------------------------------------

def test_ladder_has_five_rungs() -> None:
    ladder = build_ladder()
    assert len(ladder) == 5
    steps = [r.step for r in ladder]
    assert steps == ["1 · free", "2 · lead", "3 · entry", "4 · core", "5 · premium"]


def test_ladder_pricing_ascends() -> None:
    ladder = build_ladder()
    bands = [r.price_band for r in ladder]
    assert bands[0] == "$0"  # free
    assert "$9-$49" in bands
    assert "$99-$499" in bands
    assert "$500+" in bands


def test_ladder_custom_offers() -> None:
    ladder = build_ladder(
        business="my business",
        lead_magnet="ebook",
        entry_offer="mini-course",
        core_offer="coaching",
        premium_offer="done-for-you",
    )
    assets = [r.asset for r in ladder]
    assert "ebook" in assets
    assert "mini-course" in assets
    assert "done-for-you" in assets


def test_ladder_format() -> None:
    text = format_ladder(build_ladder())
    assert "OFFER LADDER" in text
    assert "1 · free" in text
    assert "5 · premium" in text


def test_ladder_all_pass_gate() -> None:
    ladder = build_ladder()
    assert all(r.passed_gate for r in ladder)


# --- multiplier role ---------------------------------------------------------

def test_multiplier_role_registered() -> None:
    role = role_named("multiplier")
    assert role is not None
    assert role.cadence == "on demand"
    assert role.pillar == "content"
    names = {r.name for r in all_roles()}
    assert "multiplier" in names
    assert len(names) == 11


def test_run_role_multiplier_uses_write() -> None:
    agent = FocuxAgent(llm=_StubLLM(), gate=_gate())  # type: ignore[arg-type]
    # multiplier is READ-class: ALLOW + drafts via the LLM (stub returns text)
    result = agent.run_role("multiplier", objective="multiply this insight")
    assert result.decision == "ALLOW"
    assert result.content
