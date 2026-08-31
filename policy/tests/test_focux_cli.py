"""Tests for policy/focux_cli.py — agent-native CLI layer."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy.focux_cli import (
    CliEntry,
    CliRegistry,
    install_decision,
    render_cli_skill,
    spend_decision,
)
from policy.money_gate import (
    ActionClass,
    Decision,
    MoneyGate,
    PolicyRule,
)


def _gate() -> MoneyGate:
    return MoneyGate(
        {
            ActionClass.READ: PolicyRule(ActionClass.READ, auto_approve=True),
            ActionClass.CONTENT: PolicyRule(ActionClass.CONTENT),
            ActionClass.COMMERCE: PolicyRule(ActionClass.COMMERCE),
            ActionClass.MONEY: PolicyRule(ActionClass.MONEY),
            ActionClass.ACCOUNT: PolicyRule(ActionClass.ACCOUNT),
        }
    )


def test_registry_from_list(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    reg.write_text(
        json.dumps(
            [
                {
                    "name": "exa",
                    "description": "AI-native web search",
                    "category": "search",
                    "backend": "exa-py SDK",
                    "install": "pip install cli-anything-exa",
                    "tests": 40,
                }
            ]
        ),
        encoding="utf-8",
    )
    registry = CliRegistry.from_file(reg)
    assert len(registry.entries) == 1
    assert registry.info("exa") is not None
    assert registry.info("missing") is None


def test_registry_from_nested(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    reg.write_text(
        json.dumps({"clis": [{"name": "ollama", "description": "Local LLM"}]}),
        encoding="utf-8",
    )
    registry = CliRegistry.from_file(reg)
    assert registry.info("ollama") is not None


def test_registry_from_flat_map(tmp_path: Path) -> None:
    reg = tmp_path / "registry.json"
    reg.write_text(
        json.dumps({"libreoffice": {"description": "Docs via real LO"}}),
        encoding="utf-8",
    )
    registry = CliRegistry.from_file(reg)
    entry = registry.info("libreoffice")
    assert entry is not None
    assert entry.description == "Docs via real LO"


def test_registry_search() -> None:
    entries = [
        CliEntry(name="exa", description="AI-native web search", category="search"),
        CliEntry(name="ollama", description="Local LLM inference", category="ai"),
        CliEntry(name="comfyui", description="AI image generation", category="ai"),
    ]
    registry = CliRegistry(entries=entries)
    assert [e.name for e in registry.search("inference")] == ["ollama"]
    assert [e.name for e in registry.search("image")] == ["comfyui"]
    assert [e.name for e in registry.search("web")] == ["exa"]
    assert registry.search("nothing-here") == []


def test_install_is_gated_account_review() -> None:
    gate = _gate()
    assert install_decision(gate, "exa") == Decision.REVIEW
    # Tainted install never ALLOWs either.
    assert install_decision(gate, "exa", tainted=True) == Decision.REVIEW


def test_spend_is_gated_money_review() -> None:
    gate = _gate()
    assert spend_decision(gate, "mailchimp", 5.0, "campaign") == Decision.REVIEW
    assert spend_decision(gate, "mailchimp", 5.0, "campaign", tainted=True) == Decision.REVIEW


def test_render_cli_skill() -> None:
    md = render_cli_skill("exa", "AI-native web search")
    assert md.startswith("---")
    assert "name: exa" in md
    assert "version: 1.0.0" in md
    assert "cli-hub install exa" in md
    assert "MONEY" in md


def test_render_cli_skill_rejects_bad_names() -> None:
    with pytest.raises(ValueError):
        render_cli_skill("Bad Name", "x")
    with pytest.raises(ValueError):
        render_cli_skill("", "x")
    with pytest.raises(ValueError):
        render_cli_skill("exa", "x", version="1.0")
