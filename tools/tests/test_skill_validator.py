"""Skill validator — canonical OpenClaw SKILL.md format."""
from __future__ import annotations

from pathlib import Path

from tools.skill_validator import main, validate_all, validate_skill_dir

GOOD_SKILL = """---
name: money-gate
description: Deterministic approval boundary for money and publishing actions.
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python
---

# Instructions

Never bypass the policy engine.
"""


def _write_skill(root: Path, name: str, content: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")
    return d


def test_valid_skill_has_no_errors(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "money-gate", GOOD_SKILL)
    assert validate_skill_dir(d) == []


def test_missing_skill_md_reported(tmp_path: Path) -> None:
    d = tmp_path / "orphan"
    d.mkdir()
    assert validate_skill_dir(d) != []


def test_name_must_match_directory(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "money-gate", GOOD_SKILL.replace("name: money-gate", "name: other"))
    errors = validate_skill_dir(d)
    assert any("name" in e for e in errors)


def test_version_must_be_semver(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "money-gate", GOOD_SKILL.replace("version: 1.0.0", "version: one"))
    errors = validate_skill_dir(d)
    assert any("version" in e for e in errors)


def test_missing_required_keys_reported(tmp_path: Path) -> None:
    d = _write_skill(tmp_path, "money-gate", "---\nname: money-gate\n---\n\nBody")
    errors = validate_skill_dir(d)
    assert any("description" in e for e in errors)


def test_validate_all_finds_every_error(tmp_path: Path) -> None:
    _write_skill(tmp_path, "good", GOOD_SKILL)
    bad = _write_skill(tmp_path, "bad", "no frontmatter at all")
    assert validate_all(tmp_path) != []
    assert any("bad" in e for e in validate_all(tmp_path))


def test_main_exit_codes(tmp_path: Path) -> None:
    # No args: the default skills root (this repository's skills/) is valid.
    assert main([]) == 0
    # Explicit root containing an invalid skill: exit code 1.
    _write_skill(tmp_path, "bad", "no frontmatter at all")
    assert main([str(tmp_path)]) == 1
