"""Skill loading for the FOCUX runtime — open Agent Skills format.

Reads ``SKILL.md`` folders exactly like Claude Code / Cursor / Codex / OpenClaw
/ CowAgent do: YAML frontmatter with ``name`` + ``description``, markdown body
with the instructions. Foreign keys are ignored (the runtime only reads
``name``, ``description`` and the body); nothing from a skill can grant
behavior (triggers/auto-fire/risk are never adopted) — a skill is
instructions, never a permission grant.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - optional dep
    yaml = None  # type: ignore[assignment]


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path

    def instructions(self) -> str:
        """Full text an agent should read before acting on this skill."""
        return f"# {self.name}\n{self.description}\n\n{self.body}"


def parse_skill_file(md: Path) -> Skill:
    text = md.read_text(encoding="utf-8")
    if not text.lstrip().startswith("---"):
        raise ValueError(f"{md}: missing YAML frontmatter")
    parts = text.split("---", 2)
    if yaml is None:
        raise RuntimeError("PyYAML required to parse SKILL.md (pip install pyyaml)")
    meta = yaml.safe_load(parts[1]) or {}
    name = str(meta.get("name", md.parent.name))
    description = str(meta.get("description", ""))
    body = parts[2].strip() if len(parts) > 2 else ""
    return Skill(name=name, description=description, body=body, path=md)


def load_skills(skills_dir: Path) -> list[Skill]:
    """Load every ``SKILL.md`` under ``skills_dir`` (one level deep)."""
    if not skills_dir.is_dir():
        return []
    skills: list[Skill] = []
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        if md.is_file():
            try:
                skills.append(parse_skill_file(md))
            except (ValueError, RuntimeError):
                continue  # unreadable skills are skipped, never fatal
    return skills
