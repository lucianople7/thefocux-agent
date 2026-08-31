"""FOCUX Content v1 — deterministic content ideation and hook generation.

Patterns absorbed from Charlie Hills' content-matrix and hook-generator skills
(MIT): the Justin Welsh pillars x formats matrix (32+ ideas) and the two-line
40-char hook formula. The LLM fills in the actual headlines and hooks; this
module owns the STRUCTURE — format definitions, matrix assembly, hook framing,
and validation — so the output is consistent and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# --- Content matrix -----------------------------------------------------------

#: The 8 proven formats, in canonical order (Justin Welsh matrix).
CONTENT_FORMATS: tuple[str, ...] = (
    "Actionable",
    "Motivational",
    "Analytical",
    "Contrarian",
    "Observation",
    "X vs Y",
    "Present vs Future",
    "Listicle",
)

FORMAT_DEFINITIONS: dict[str, str] = {
    "Actionable": "Ultra-specific how-to. Teaches the reader to do one thing.",
    "Motivational": "Inspirational story about someone who did something "
    "extraordinary in the niche.",
    "Analytical": "Breakdown of why something works the way it does.",
    "Contrarian": "Go against the common advice in the niche and back it up.",
    "Observation": "A hidden, silent, or underdiscussed trend the user noticed.",
    "X vs Y": "Compare two entities (tools, styles, frameworks, companies).",
    "Present vs Future": "Current state vs a specific prediction, with the why.",
    "Listicle": "A list of resources, tips, mistakes, lessons, or steps.",
}


@dataclass(frozen=True)
class MatrixCell:
    pillar: str
    format_name: str
    headline: str  # a specific headline, not a theme

    def as_dict(self) -> dict[str, str]:
        return {
            "pillar": self.pillar,
            "format": self.format_name,
            "headline": self.headline,
        }


class ContentMatrix:
    """Pillars x formats ideation. Requires 3-5 pillars (dilutes beyond)."""

    def __init__(self, pillars: tuple[str, ...]) -> None:
        if not 3 <= len(pillars) <= 5:
            raise ValueError("ContentMatrix requires 3 to 5 pillars")
        self._pillars = tuple(pillars)

    @property
    def pillars(self) -> tuple[str, ...]:
        return self._pillars

    @property
    def formats(self) -> tuple[str, ...]:
        return CONTENT_FORMATS

    def dimensions(self) -> tuple[int, int]:
        return len(self._pillars), len(CONTENT_FORMATS)

    def fill(
        self,
        headline_for: Callable[[str, str], str],
    ) -> list[MatrixCell]:
        """Fill every cell; ``headline_for(pillar, format) -> headline``.

        The callback is the LLM-backed ideation step; validation here keeps
        the matrix honest (no blank cells, no duplicated ideas per pillar).
        """
        cells: list[MatrixCell] = []
        seen: dict[str, set[str]] = {p: set() for p in self._pillars}
        for pillar in self._pillars:
            for fmt in CONTENT_FORMATS:
                headline = (headline_for(pillar, fmt) or "").strip()
                if not headline:
                    raise ValueError(f"blank headline for {pillar} x {fmt}")
                if headline in seen[pillar]:
                    raise ValueError(
                        f"duplicate idea for pillar '{pillar}': {headline}"
                    )
                seen[pillar].add(headline)
                cells.append(MatrixCell(pillar, fmt, headline))
        return cells

    def render_markdown(self, cells: list[MatrixCell]) -> str:
        """Render the matrix as a plain markdown table (no code fence)."""
        header = "| Pillar | " + " | ".join(CONTENT_FORMATS) + " |"
        sep = "|---|" + "---|" * len(CONTENT_FORMATS)
        rows: dict[str, dict[str, str]] = {
            p: {f: "" for f in CONTENT_FORMATS} for p in self._pillars
        }
        for cell in cells:
            rows[cell.pillar][cell.format_name] = cell.headline
        lines = [header, sep]
        for pillar in self._pillars:
            lines.append(
                "| " + pillar + " | "
                + " | ".join(rows[pillar][f] for f in CONTENT_FORMATS)
                + " |"
            )
        return "\n".join(lines)


# --- Hook generator -----------------------------------------------------------

#: Hook-style templates keyed by the observed performer styles (Charlie data:
#: number-led 31%, bold claim 27%, contrarian 18% are the top performers).
HOOK_FRAMES: tuple[str, ...] = (
    "number-led",
    "bold-claim",
    "contrarian",
    "question",
    "personal-story",
    "news",
)

HOOK_OPENERS: dict[str, str] = {
    "number-led": "The {n}-step {topic} system nobody talks about",
    "bold-claim": "{topic} is not what you think it is",
    "contrarian": "Stop doing {topic} the way everyone tells you",
    "question": "Why does {topic} keep failing for smart people?",
    "personal-story": "I ignored {topic} for a year. That was the mistake",
    "news": "Something just changed in {topic}. Most people missed it",
}

HOOK_CONTRASTS: dict[str, str] = {
    "number-led": "Here is the {n}-step system I used",
    "bold-claim": "Here is what actually works instead",
    "contrarian": "Here is what I do instead",
    "question": "The answer is simpler than you think",
    "personal-story": "Here is what happened when I changed",
    "news": "Here is what it means for you",
}


@dataclass(frozen=True)
class Hook:
    frame: str
    opening: str  # ~40 chars
    contrast: str  # ~40 chars

    @property
    def two_line(self) -> str:
        return f"{self.opening}\n{self.contrast}"

    def as_dict(self) -> dict[str, str]:
        return {"frame": self.frame, "opening": self.opening, "contrast": self.contrast}


def generate_hooks(topic: str, *, number: int = 6) -> list[Hook]:
    """Six two-line hooks: a 40-char opening + a 40-char contrast line.

    The template substitution is deterministic; the LLM may later rewrite
    each hook in the user's voice (voice.md) before publishing.
    """
    clean = " ".join(topic.strip().split())
    if not clean:
        raise ValueError("topic cannot be blank")
    hooks: list[Hook] = []
    for frame in HOOK_FRAMES:
        opener = HOOK_OPENERS[frame].format(topic=clean, n=3)
        contrast = HOOK_CONTRASTS[frame].format(topic=clean, n=3)
        hooks.append(Hook(frame=frame, opening=opener, contrast=contrast))
    return hooks[:number]


def render_hooks(hooks: list[Hook]) -> str:
    return "\n\n".join(f"[{h.frame}]\n{h.two_line}" for h in hooks)
