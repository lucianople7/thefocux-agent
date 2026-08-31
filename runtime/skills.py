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


# --- Skill crystallization (GenericAgent pattern, human-gated) ----------------

DRAFT_STATUS = "draft"
ACTIVE_STATUS = "active"


def render_skill_markdown(
    name: str,
    description: str,
    body: str,
    *,
    status: str = ACTIVE_STATUS,
    version: str = "1.0.0",
) -> str:
    """Render a SKILL.md with the canonical frontmatter (validator-compatible)."""
    return (
        f"---\n"
        f"name: {name}\n"
        f"description: >-\n"
        f"  {description.strip()}\n"
        f"version: {version}\n"
        f"metadata:\n"
        f"  focux:\n"
        f"    status: {status}\n"
        f"---\n\n"
        f"{body.strip()}\n"
    )


def crystallize_skill(
    drafts_dir: Path,
    *,
    name: str,
    description: str,
    body: str,
) -> Path:
    """Write a crystallized skill as a DRAFT (never auto-activated).

    Pattern from GenericAgent (MIT): after solving a task the first time, the
    agent materializes the executed path as a reusable skill. FOCUX writes it
    to ``skills-draft/`` with ``metadata.focux.status: draft`` — the active
    catalog (``skills/``) is untouched until a human promotes it.
    """
    import re

    if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        raise ValueError("skill name must be 1-64 lowercase letters/numbers/hyphens")
    target = drafts_dir / name / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_skill_markdown(name, description, body, status=DRAFT_STATUS),
        encoding="utf-8",
    )
    return target


def promote_skill(
    drafts_dir: Path,
    skills_dir: Path,
    name: str,
) -> Path:
    """Promote a DRAFT to the active catalog (HUMAN review step).

    Reads the draft, flips ``metadata.focux.status`` to ``active`` and writes
    it into ``skills/<name>/SKILL.md``. The draft stays in ``skills-draft/``
    as the audit trail. Raises if the draft does not exist or is not a draft.
    """
    draft_md = drafts_dir / name / "SKILL.md"
    if not draft_md.is_file():
        raise FileNotFoundError(f"no draft skill: {name}")
    text = draft_md.read_text(encoding="utf-8")
    if "status: draft" not in text:
        raise ValueError(f"{name} is not a draft (refusing to promote)")
    active_md = skills_dir / name / "SKILL.md"
    active_md.parent.mkdir(parents=True, exist_ok=True)
    promoted = text.replace("status: draft", "status: active")
    active_md.write_text(promoted, encoding="utf-8")
    return active_md


def list_drafts(drafts_dir: Path) -> list[Skill]:
    """List crystallized drafts (for human review)."""
    return load_skills(drafts_dir)
