"""Tests for FOCUX memory — SQLite stores, workspaces, retrieval gate."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.memory import FocuxMemory  # noqa: E402


@pytest.fixture()
def mem(tmp_path: Path) -> FocuxMemory:
    m = FocuxMemory(tmp_path / "focux.db")
    yield m
    m.close()


def test_episodic_roundtrip(mem: FocuxMemory) -> None:
    mem.remember_event("content", "draft", {"topic": "AI agents"})
    mem.remember_event("content", "publish", {"platform": "linkedin"})
    events = mem.recent_events("content")
    assert len(events) == 2
    assert events[0].kind == "publish"  # newest first
    assert events[1].data["topic"] == "AI agents"


def test_semantic_upsert(mem: FocuxMemory) -> None:
    mem.remember_fact("billing", "currency", "EUR")
    mem.remember_fact("billing", "currency", "USD")  # upsert
    facts = mem.facts("billing")
    assert len(facts) == 1
    assert facts[0].value == "USD"


def test_workspaces_isolate(mem: FocuxMemory) -> None:
    mem.remember_fact("billing", "vat", "21%")
    mem.remember_fact("content", "vat", "n/a")
    assert len(mem.facts("billing")) == 1
    assert len(mem.facts("content")) == 1
    assert mem.facts("billing")[0].value == "21%"


def test_procedural_counters(mem: FocuxMemory) -> None:
    mem.learn_procedure(
        "content", "newsletter-draft",
        ("load voice", "draft in voice", "quality gate"),
    )
    mem.record_outcome("content", "newsletter-draft", success=True)
    mem.record_outcome("content", "newsletter-draft", success=True)
    mem.record_outcome("content", "newsletter-draft", success=False)
    procs = mem.procedures("content")
    assert len(procs) == 1
    assert procs[0].success_count == 2
    assert procs[0].fail_count == 1
    assert procs[0].steps == ("load voice", "draft in voice", "quality gate")


def test_gate_keywords_trigger_retrieval(mem: FocuxMemory) -> None:
    should, query = mem.should_retrieve("what is 2 + 2?")
    assert not should
    should, query = mem.should_retrieve("what's the price of our product?")
    assert should
    assert "price" in query


def test_gate_fails_open_without_llm(mem: FocuxMemory) -> None:
    # No LLM gate configured: non-keyword messages simply don't retrieve.
    should, _ = mem.should_retrieve("tell me a joke about ducks")
    assert not should


def test_recollect_returns_pack(mem: FocuxMemory) -> None:
    mem.remember_fact("content", "north_star", "newsletter-first")
    pack = mem.recollect("our campaign metrics?", "content")
    assert pack["retrieved"] is True
    assert any(f["key"] == "north_star" for f in pack["facts"])


def test_recollect_skips_when_gate_says_no(mem: FocuxMemory) -> None:
    pack = mem.recollect("explain quantum computing", "content")
    assert pack["retrieved"] is False
    assert pack["query"] == ""


def test_context_block_empty_when_no_recall(mem: FocuxMemory) -> None:
    block = mem.context_block("what is the capital of France?", "content")
    assert block == ""


def test_context_block_includes_facts(mem: FocuxMemory) -> None:
    mem.remember_fact("billing", "invoice_prefix", "FOC-2026")
    block = mem.context_block("send the invoice", "billing")
    assert "## Memory" in block
    assert "invoice_prefix" in block
    assert "FOC-2026" in block


def test_persistence_across_reopen(tmp_path: Path) -> None:
    db = tmp_path / "focux.db"
    m1 = FocuxMemory(db)
    m1.remember_fact("content", "voice", "blunt")
    m1.close()
    m2 = FocuxMemory(db)
    facts = m2.facts("content")
    m2.close()
    assert len(facts) == 1
    assert facts[0].value == "blunt"


def test_llm_gate_used_when_configured(tmp_path: Path) -> None:
    class StubGate:
        def complete(self, messages):  # type: ignore[no-untyped-def]
            return '{"retrieve": true, "query": "client history", "reason": "asks about client"}'

    m = FocuxMemory(tmp_path / "focux.db", gate_llm=StubGate())  # type: ignore[arg-type]
    # No deterministic keyword ("alpha bravo") -> exercises the LLM gate.
    should, query = m.should_retrieve("alpha bravo charlie delta")
    m.close()
    assert should
    assert "client history" in query
