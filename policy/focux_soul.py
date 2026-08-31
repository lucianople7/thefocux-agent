"""FOCUX Soul — deterministic SOUL.md model, validation and sanitization.

Pattern ported from Conway Automaton `src/soul/validator.ts` (MIT) into pure
Python: size limits, structural requirements, and injection-pattern defense.
NO LLM in the check — the identity file is guarded by regex, never by the
thing it describes.

A SOUL.md is the evolving identity document of a FOCUX business agent:
core purpose, values, behavioral guidelines, personality, boundaries,
strategy. It is validated on every write; anything that fails is rejected or
sanitized, and the audit log records what was stripped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# --- Size limits (chars / item counts) ----------------------------------------

LIMITS = {
    "core_purpose": 2000,
    "values": 20,
    "behavioral_guidelines": 30,
    "personality": 1000,
    "boundaries": 20,
    "strategy": 3000,
}


# --- Injection patterns (ported from Automaton validator.ts) ------------------

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Prompt boundaries
    re.compile(r"</?system>", re.I),
    re.compile(r"</?prompt>", re.I),
    re.compile(r"\[INST\]", re.I),
    re.compile(r"\[/INST\]", re.I),
    re.compile(r"<<SYS>>", re.I),
    re.compile(r"<</SYS>>", re.I),
    re.compile(r"\[/?SYSTEM\]", re.I),
    re.compile(r"END\s+OF\s+(SYSTEM|PROMPT)", re.I),
    re.compile(r"BEGIN\s+NEW\s+(PROMPT|INSTRUCTIONS?)", re.I),
    # ChatML markers
    re.compile(r"<\|im_start\|>", re.I),
    re.compile(r"<\|im_end\|>", re.I),
    re.compile(r"<\|endoftext\|>", re.I),
    # Tool call syntax
    re.compile(r'\{"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:'),
    re.compile(r"\btool_call\b", re.I),
    re.compile(r"\bfunction_call\b", re.I),
    # System overrides
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)", re.I),
    re.compile(r"override\s+(all\s+)?safety", re.I),
    re.compile(r"bypass\s+(all\s+)?restrictions?", re.I),
    re.compile(r"new\s+instructions?:", re.I),
    re.compile(r"your\s+real\s+instructions?\s+(are|is)", re.I),
    # Encoding evasion
    re.compile(r"\x00"),
    re.compile(r"\u200b"),
    re.compile(r"\u200c"),
    re.compile(r"\u200d"),
    re.compile(r"\ufeff"),
)


@dataclass
class SoulModel:
    core_purpose: str = ""
    values: list[str] = field(default_factory=list)
    behavioral_guidelines: list[str] = field(default_factory=list)
    personality: str = ""
    boundaries: list[str] = field(default_factory=list)
    strategy: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "core_purpose": self.core_purpose,
            "values": list(self.values),
            "behavioral_guidelines": list(self.behavioral_guidelines),
            "personality": self.personality,
            "boundaries": list(self.boundaries),
            "strategy": self.strategy,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SoulModel":
        return cls(
            core_purpose=str(data.get("core_purpose", "")),
            values=[str(v) for v in data.get("values", [])],
            behavioral_guidelines=[
                str(v) for v in data.get("behavioral_guidelines", [])
            ],
            personality=str(data.get("personality", "")),
            boundaries=[str(v) for v in data.get("boundaries", [])],
            strategy=str(data.get("strategy", "")),
        )


@dataclass(frozen=True)
class SoulValidationResult:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    sanitized: SoulModel


def contains_injection_patterns(text: str) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def _strip_injection(text: str) -> str:
    if not text:
        return text
    cleaned = text
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def validate_soul(soul: SoulModel) -> SoulValidationResult:
    """Validate a SoulModel. Never throws; returns a result."""
    errors: list[str] = []
    warnings: list[str] = []

    if not soul.core_purpose.strip():
        errors.append("Core purpose is required")
    if len(soul.core_purpose) > LIMITS["core_purpose"]:
        errors.append(
            f"Core purpose exceeds {LIMITS['core_purpose']} chars "
            f"({len(soul.core_purpose)})"
        )
    if len(soul.values) > LIMITS["values"]:
        errors.append(f"Too many values ({len(soul.values)}, max {LIMITS['values']})")
    if len(soul.behavioral_guidelines) > LIMITS["behavioral_guidelines"]:
        errors.append(
            f"Too many behavioral guidelines "
            f"({len(soul.behavioral_guidelines)}, max "
            f"{LIMITS['behavioral_guidelines']})"
        )
    if len(soul.personality) > LIMITS["personality"]:
        errors.append(
            f"Personality exceeds {LIMITS['personality']} chars "
            f"({len(soul.personality)})"
        )
    if len(soul.boundaries) > LIMITS["boundaries"]:
        errors.append(
            f"Too many boundaries ({len(soul.boundaries)}, max {LIMITS['boundaries']})"
        )
    if len(soul.strategy) > LIMITS["strategy"]:
        warnings.append(
            f"Strategy exceeds {LIMITS['strategy']} chars "
            f"({len(soul.strategy)})"
        )

    # Injection detection per section.
    text_sections = {
        "core_purpose": soul.core_purpose,
        "personality": soul.personality,
        "strategy": soul.strategy,
    }
    for name, content in text_sections.items():
        if content and contains_injection_patterns(content):
            errors.append(f"Injection pattern detected in {name}")
    list_sections = {
        "values": soul.values,
        "behavioral_guidelines": soul.behavioral_guidelines,
        "boundaries": soul.boundaries,
    }
    for name, items in list_sections.items():
        if any(contains_injection_patterns(item) for item in items):
            errors.append(f"Injection pattern detected in {name}")

    return SoulValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        sanitized=sanitize_soul(soul),
    )


def sanitize_soul(soul: SoulModel) -> SoulModel:
    """Strip injection patterns and enforce size limits; returns a clean copy."""
    return SoulModel(
        core_purpose=_strip_injection(soul.core_purpose)[: LIMITS["core_purpose"]],
        values=[_strip_injection(v)[:500] for v in soul.values][: LIMITS["values"]],
        behavioral_guidelines=[
            _strip_injection(v)[:500] for v in soul.behavioral_guidelines
        ][: LIMITS["behavioral_guidelines"]],
        personality=_strip_injection(soul.personality)[: LIMITS["personality"]],
        boundaries=[_strip_injection(v)[:500] for v in soul.boundaries][
            : LIMITS["boundaries"]
        ],
        strategy=_strip_injection(soul.strategy)[: LIMITS["strategy"]],
    )


def parse_soul_markdown(text: str) -> SoulModel:
    """Parse a SOUL.md (## Section headings) into a SoulModel.

    Supports the documented section names; unknown sections are ignored.
    This keeps the identity file human-readable AND machine-validated.
    """
    soul = SoulModel()
    current: str | None = None
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            heading = line[3:].strip().lower().replace(" ", "_")
            if heading in {
                "core_purpose",
                "values",
                "behavioral_guidelines",
                "personality",
                "boundaries",
                "strategy",
            }:
                current = heading
            else:
                current = None
            continue
        if current is None or not line.strip() or line.lstrip().startswith("#"):
            continue
        content = line.strip().lstrip("-* ").strip()
        if not content:
            continue
        if current in ("values", "behavioral_guidelines", "boundaries"):
            getattr(soul, current).append(content)
        else:
            setattr(soul, current, (getattr(soul, current) + " " + content).strip())
    return soul
