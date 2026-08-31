"""Validate skills/*/SKILL.md against the canonical OpenClaw skill format.

Checks: SKILL.md exists; YAML frontmatter parses; required keys name,
description, version present; name matches the parent directory and matches
[a-z0-9-]{1,64}; version is semver. Uses PyYAML (pip install pyyaml if missing).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment fix, not logic
    yaml = None  # type: ignore[assignment]

_REQUIRED = ("name", "description", "version")
_NAME_RE = re.compile(r"[a-z0-9-]{1,64}")
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"{skill_dir.name}: missing SKILL.md"]
    text = md.read_text(encoding="utf-8")
    if not text.lstrip().startswith("---"):
        return [f"{skill_dir.name}: missing YAML frontmatter"]
    parts = text.split("---", 2)
    if yaml is None:
        return [f"{skill_dir.name}: PyYAML not installed (pip install pyyaml)"]
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception as exc:  # noqa: BLE001 - report any parse failure
        return [f"{skill_dir.name}: invalid YAML frontmatter: {exc}"]
    if not isinstance(meta, dict):
        return [f"{skill_dir.name}: frontmatter must be a mapping"]
    for key in _REQUIRED:
        if not meta.get(key):
            errors.append(f"{skill_dir.name}: missing frontmatter key '{key}'")
    name = str(meta.get("name", ""))
    if name != skill_dir.name:
        errors.append(f"{skill_dir.name}: frontmatter name '{name}' != directory '{skill_dir.name}'")
    if not _NAME_RE.fullmatch(name):
        errors.append(f"{skill_dir.name}: name must be 1-64 lowercase letters/numbers/hyphens")
    version = str(meta.get("version", ""))
    if not _VERSION_RE.fullmatch(version):
        errors.append(f"{skill_dir.name}: version must be semver (e.g. 1.0.0)")
    return errors


def validate_all(skills_root: Path) -> list[str]:
    if not skills_root.is_dir():
        return [f"{skills_root}: not a directory"]
    errors: list[str] = []
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        errors.extend(validate_skill_dir(skill_dir))
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent / "skills"
    errors = validate_all(root)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} validation error(s) in {root}", file=sys.stderr)
        return 1
    print(f"OK: all skills valid in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
