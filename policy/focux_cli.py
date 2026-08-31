"""FOCUX CLI — agent-native CLI layer (skeleton).

Pattern absorbed from CLI-Anything (Apache-2.0): agents drive real software
through structured CLIs over real backends — deterministic, JSON-native,
self-describing. This module owns the FOCUX side of that contract:

- registry discovery (CLI-Hub style: list/search/info)
- INSTALL gating through the money-gate (installing tooling is a system
  change: ACCOUNT class, REVIEW at L1)
- a validated SKILL.md wrapper so any SKILL-compatible shell can load it
- spend gating for CLIs that cost money (MONEY class)

The actual harnesses (`cli-anything-*`) come from CLI-Hub / community; FOCUX
never reimplements the software it drives.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from policy.money_gate import Action, ActionClass, Decision, MoneyGate


@dataclass(frozen=True)
class CliEntry:
    name: str
    description: str = ""
    category: str = "general"
    backend: str = ""
    install: str = ""
    tests: int = 0

    @classmethod
    def from_registry(cls, raw: dict[str, object]) -> "CliEntry":
        return cls(
            name=str(raw.get("name", "")),
            description=str(raw.get("description", "")),
            category=str(raw.get("category", "general")),
            backend=str(raw.get("backend", "")),
            install=str(raw.get("install", "")),
            tests=int(raw.get("tests", 0) or 0),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "backend": self.backend,
            "install": self.install,
            "tests": self.tests,
        }


@dataclass
class CliRegistry:
    """Registry-aware view over CLI-Hub style JSON registries."""

    entries: list[CliEntry] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "CliRegistry":
        data = json.loads(path.read_text(encoding="utf-8"))
        entries: list[CliEntry] = []
        if isinstance(data, list):
            entries = [CliEntry.from_registry(item) for item in data]
        elif isinstance(data, dict):
            # Some registries nest under a key; accept {"clis": [...]} or
            # {"packages": [...]} or a flat mapping name -> entry.
            for key in ("clis", "packages", "entries"):
                items = data.get(key)
                if isinstance(items, list):
                    entries = [CliEntry.from_registry(i) for i in items]
                    break
            else:
                for name, raw in data.items():
                    if isinstance(raw, dict):
                        entries.append(
                            CliEntry.from_registry({"name": name, **raw})
                        )
        return cls(entries=entries)

    def search(self, query: str) -> list[CliEntry]:
        q = query.lower()
        return [
            e
            for e in self.entries
            if q in e.name.lower()
            or q in e.description.lower()
            or q in e.category.lower()
        ]

    def info(self, name: str) -> CliEntry | None:
        for e in self.entries:
            if e.name == name:
                return e
        return None


# --- Gating -------------------------------------------------------------------

#: Installing tooling changes the system: ACCOUNT class, REVIEW at L1.
def default_cli_rules(gate: MoneyGate) -> dict[ActionClass, object]:
    return {}


def install_decision(gate: MoneyGate, cli_name: str, *, tainted: bool = False) -> Decision:
    """Gate a CLI install through the money-gate (system change)."""
    return gate.decide(
        Action(
            action_class=ActionClass.ACCOUNT,
            amount=0.0,
            target=f"cli-install:{cli_name}",
            idempotency_key=f"cli-install:{cli_name}",
        ),
        tainted=tainted,
    )


def spend_decision(
    gate: MoneyGate,
    cli_name: str,
    amount: float,
    target: str,
    *,
    tainted: bool = False,
) -> Decision:
    """Gate a CLI invocation that spends money (MONEY class)."""
    return gate.decide(
        Action(
            action_class=ActionClass.MONEY,
            amount=amount,
            target=f"cli:{cli_name}:{target}",
            idempotency_key=f"cli:{cli_name}:{target}",
        ),
        tainted=tainted,
    )


# --- SKILL.md wrapper ---------------------------------------------------------

_SKILL_RE = re.compile(r"[a-z0-9-]{1,64}")


def render_cli_skill(cli_name: str, description: str, version: str = "1.0.0") -> str:
    """Generate the canonical SKILL.md for an installed CLI.

    Mirrors CLI-Anything's skill_generator.py idea: a SKILL-compatible shell
    discovers the CLI via its SKILL.md (our validator enforces the format).
    """
    if not _SKILL_RE.fullmatch(cli_name):
        raise ValueError("cli_name must be 1-64 lowercase letters/numbers/hyphens")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must be semver (e.g. 1.0.0)")
    return f"""---
name: {cli_name}
description: >
  Agent-native CLI for {description}. Use the <code>cli-anything-{cli_name}</code>
  command (REPL without args, --json for machine output). Install is gated by
  the money-gate; spending invocations are MONEY-class actions.
version: {version}
---

# {cli_name}

Install: <code>cli-hub install {cli_name}</code> (REVIEW via money-gate).

Usage:
- <code>cli-anything-{cli_name}</code> — interactive REPL
- <code>cli-anything-{cli_name} --json &lt;command&gt;</code> — machine output
- <code>cli-anything-{cli_name} --help</code> — discover capabilities

Any invocation that spends money must pass the money-gate (MONEY class).
"""
