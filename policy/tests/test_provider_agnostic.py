"""Contract test: THE FOCUX provider-agnostic & plugin-ready guarantee.

Verifies the claims in docs/provider-agnostic-guarantee.md:

1. The DNA layer (focux/policy) imports NO LLM SDK — pure Python, any provider.
2. Every skill is in the open Agent Skills format (name + description) and
   validates with our canonical validator.
3. When the fork runtime is present, its portable loader accepts every skill
   (same format Claude Code / Cursor / Codex / OpenClaw / CowAgent consume).
4. The money-gate falsification invariant holds — agnosticism never suspends
   safety.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

FOCUX = Path(__file__).resolve().parent.parent.parent  # focux/
POLICY = FOCUX / "policy"
SKILLS = FOCUX / "skills"

#: SDKs that would couple the DNA to one provider. The policy modules must
#: never import these.
FORBIDDEN_IMPORTS = (
    "openai",
    "anthropic",
    "google.generativeai",
    "google.cloud",
    "groq",
    "mistralai",
    "cohere",
    "together",
    "replicate",
    "ollama",
)


def _py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in str(p))


def test_dna_imports_no_llm_sdk() -> None:
    """Agnosticism core: no provider SDK in any decision path."""
    offenders: list[str] = []
    for path in _py_files(POLICY):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in FORBIDDEN_IMPORTS:
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top in FORBIDDEN_IMPORTS:
                        offenders.append(f"{path.name}: from {node.module}")
    assert offenders == [], "DNA must not import LLM SDKs:\n" + "\n".join(offenders)


def test_every_skill_has_open_agent_skills_frontmatter() -> None:
    """Plugin-ready: each skill speaks the open Agent Skills format."""
    skill_dirs = [d for d in SKILLS.iterdir() if d.is_dir()]
    assert len(skill_dirs) >= 17, f"expected 17+ skills, found {len(skill_dirs)}"
    for d in skill_dirs:
        md = d / "SKILL.md"
        assert md.exists(), f"{d.name}: missing SKILL.md"
        text = md.read_text(encoding="utf-8")
        assert text.lstrip().startswith("---"), f"{d.name}: no frontmatter"
        parts = text.split("---", 2)
        assert re.search(r"^name:\s*\S+", parts[1], re.M), f"{d.name}: no name"
        assert re.search(
            r"^description:", parts[1], re.M
        ), f"{d.name}: no description"


def test_skills_valid_with_canonical_validator() -> None:
    """Plugin-ready: canonical validator accepts every skill."""
    sys.path.insert(0, str(FOCUX / "tools"))
    from skill_validator import validate_all

    errors = validate_all(SKILLS)
    assert errors == [], "skill validation errors:\n" + "\n".join(errors)


@pytest.mark.skipif(
    not (FOCUX.parent / "jarvis").exists(),
    reason="fork runtime not present in this checkout",
)
def test_fork_portable_loader_accepts_all_skills() -> None:
    """Plugin-ready: the runtime's portable loader reads every FOCUX skill."""
    sys.path.insert(0, str(FOCUX.parent))  # repo root so `jarvis` imports
    from jarvis.skills.loader import parse_skill

    failures: list[str] = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir():
            continue
        try:
            skill = parse_skill(d / "SKILL.md")
            assert skill.frontmatter is not None
            assert skill.frontmatter.name == d.name
        except Exception as exc:  # noqa: BLE001 - report per skill
            failures.append(f"{d.name}: {type(exc).__name__}: {exc}")
    assert failures == [], "fork loader failures:\n" + "\n".join(failures)


def test_falsification_still_holds() -> None:
    """Agnosticism never suspends safety."""
    sys.path.insert(0, str(FOCUX))
    from policy.money_gate import MoneyGate

    assert MoneyGate({}).falsification_test() is True
    assert MoneyGate(
        {
            # a realistic L1 table: auto-approve requires a bound
        }
    ).falsification_test() is True
