"""THE FOCUX LESSONS — work memory that compounds (Graphify reflect pattern).

Pattern absorbed from Graphify: record how real Q&A / work turned out
(`save-result`), then `reflect` aggregates the outcomes into a lessons doc
that future sessions consult. THE FOCUX keeps lessons as memory facts and
writes `.focux/lessons.md` — the brain's accumulated wisdom, used by
evolution and by any agent that reads focus.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def save_lesson(memory, workspace: str, lesson: str, *,
                outcome: str = "useful") -> dict[str, Any]:
    """Record a lesson (memory fact, kind namespace `lesson:<slug>`)."""
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", lesson.lower()).strip("-")[:48] or "lesson"
    key = f"lesson:{slug}"
    memory.remember_fact(workspace, key, lesson)
    return {"key": key, "lesson": lesson, "outcome": outcome}


def lessons(memory, workspace: str) -> list[dict[str, str]]:
    """All saved lessons (facts keyed lesson:*)."""
    return [
        {"key": f.key, "lesson": f.value}
        for f in memory.facts(workspace)
        if f.key.startswith("lesson:")
    ]


def reflect(memory, workspace: str, *, out: Path | None = None) -> Path:
    """Aggregate saved lessons into a markdown doc (.focux/lessons.md)."""
    items = lessons(memory, workspace)
    target = out or (Path.cwd() / ".focux" / "lessons.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not items:
        target.write_text(
            "# THE FOCUX LESSONS\n\n(no lessons yet - save one with "
            "`focux lesson '<que aprendiste>'`)\n", encoding="utf-8")
        return target
    lines = [
        "# THE FOCUX LESSONS - wisdom accumulated from real work",
        "",
        f"Lessons: {len(items)}",
        "",
    ]
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. **{item['key'].replace('lesson:', '')}** - "
                     f"{item['lesson']}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
