"""FOCUX Self-Modification — append-only audit + rate limits (Automaton pattern).

The agent can crystallize skills and change its own behavior — but every
modification is recorded in an append-only log, protected files are never
touched, and rate limits prevent runaway self-modification. The human remains
the release authority (drafts are never auto-activated).

Pattern absorbed from Conway Automaton `src/self-mod/` (MIT), adapted: our
audit is JSONL (plain, greppable, yours), and "self-modification" here means
skill crystallization + procedure learning, not code changes to the runtime.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Guards parallel appends within one process (os.write is atomic per call;
#: the lock prevents interleaved writes from threads).
_APPEND_LOCK = threading.Lock()


@dataclass(frozen=True)
class SelfModEntry:
    id: str
    timestamp: str
    kind: str  # skill_crystallized | procedure_learned | draft_promoted
    description: str
    reversible: bool = True
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "description": self.description,
            "reversible": self.reversible,
            "data": self.data,
        }


class SelfModLog:
    """Append-only JSONL audit of the agent's self-modifications."""

    def __init__(self, path: str | Path = "memory/selfmod.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        kind: str,
        description: str,
        *,
        reversible: bool = True,
        data: dict[str, Any] | None = None,
    ) -> SelfModEntry:
        """Append a modification entry. Never edits history.

        ``data`` is serialized safely: non-JSON values degrade to their str
        form instead of raising (the audit must never break the agent).
        """
        entry = SelfModEntry(
            id=_new_id(),
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            kind=kind,
            description=description,
            reversible=reversible,
            data=_safe_data(data),
        )
        line = (json.dumps(entry.as_dict(), ensure_ascii=False) + "\n").encode("utf-8")
        # REGRESSION round 5: parallel appends lost entries. Each append must
        # be ONE atomic write: thread lock + a single os.write on an O_APPEND
        # fd (append mode makes multi-process writes atomic too).
        with _APPEND_LOCK:
            fd = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
        return entry

    def entries(self, limit: int = 50) -> list[SelfModEntry]:
        if not self._path.is_file():
            return []
        out: list[SelfModEntry] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                out.append(SelfModEntry(**raw))
            except (json.JSONDecodeError, TypeError):
                continue
        return out[-limit:]

    def count(self, kind: str | None = None) -> int:
        entries = self.entries(limit=10_000)
        if kind is None:
            return len(entries)
        return sum(1 for e in entries if e.kind == kind)


def _new_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


def _safe_data(data: dict[str, Any] | None) -> dict[str, Any]:
    """Make audit data JSON-safe: non-serializable values degrade to str."""
    if not data:
        return {}
    safe: dict[str, Any] = {}
    for key, value in data.items():
        try:
            json.dumps(value)
            safe[key] = value
        except (TypeError, ValueError):
            safe[key] = f"<non-serializable:{type(value).__name__}>"
    return safe


class RateLimiter:
    """Per-window rate limit for self-modification (anti-runaway)."""

    def __init__(self, window_seconds: int = 3600, max_ops: int = 10) -> None:
        self._window = window_seconds
        self._max = max_ops
        self._times: list[float] = []

    def allow(self, now: float) -> bool:
        cutoff = now - self._window
        self._times = [t for t in self._times if t > cutoff]
        if len(self._times) >= self._max:
            return False
        self._times.append(now)
        return True

    @property
    def remaining(self) -> int:
        return max(0, self._max - len(self._times))


#: Protected paths the agent may never modify through learn()/promote().
PROTECTED_PATHS: tuple[str, ...] = (
    "constitution.md",
    "policy/constitution.py",
    "policy/money_gate.py",
    "AGENTS.md",
)


def is_protected(rel_path: str) -> bool:
    return rel_path.replace("\\", "/") in PROTECTED_PATHS
