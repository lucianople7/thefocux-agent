"""FOCUX memory — local-first SQLite stores, pattern from Waku (MIT) + Memmy (MIT).

Three stores in ONE local SQLite file (the business owns its data):

- **episodic**: events with timestamps (tool calls, decisions, outcomes) —
  searchable by workspace + kind.
- **semantic**: key-value facts (business, audience, preferences) by workspace.
- **procedural**: named step-by-step procedures with success/failure counters
  (what worked wins; what failed is flagged).

Discipline (from Waku's retrieval gate): before hitting the stores, a cheap
decision says whether THIS message needs memory at all — retrieval is not
default-on (slow + biases the answer). The gate **fails open**: on any error
we retrieve, because a stale memory beats a lost one. Unlike the money-gate,
this gate is an efficiency decision, never a safety boundary — safety gates
never fail open.

Workspaces (from Memmy): isolate business domains (billing, customers,
content, research) so context never leaks across concerns.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .llm import LLMClient

#: Deterministic gate keywords: messages mentioning business context trigger
#: retrieval. Cheap, local, no LLM required.
_RETRIEVAL_KEYWORDS = (
    "client", "cliente", "customer", "precio", "price", "venta", "sale",
    "product", "producto", "campa", "campaign", "post", "contenido", "content",
    "email", "correo", "offer", "oferta", "metric", "métrica", "métricas",
    "recuerda", "remember", "memoria", "memory", "reunión", "meeting",
    "factura", "invoice", "stock", "inventario", "audiencia", "audience",
)

_GATE_PROMPT = """\
You are a retrieval gate for a business agent's long-term memory.
Given the user's message, decide if answering well requires stored business
memories (facts about clients, products, prices, campaigns, metrics, or past
events).

Reply with ONLY this JSON, nothing else:
{{"retrieve": true/false, "query": "<search keywords if true, else empty>", "reason": "<5 words>"}}

General knowledge, math, small talk, or self-contained requests → false.
Anything referencing the business's life, people, plans, or history → true.

User message: {message}"""


@dataclass(frozen=True)
class MemoryEvent:
    workspace: str
    kind: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "kind": self.kind,
            "data": self.data,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class MemoryFact:
    workspace: str
    key: str
    value: str
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class Procedure:
    workspace: str
    name: str
    steps: tuple[str, ...]
    success_count: int = 0
    fail_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "name": self.name,
            "steps": list(self.steps),
            "success_count": self.success_count,
            "fail_count": self.fail_count,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class FocuxMemory:
    """SQLite-backed memory. One file, owned by the business."""

    def __init__(
        self,
        db_path: str | Path = "memory/focux.db",
        *,
        gate_llm: LLMClient | None = None,
        gate_model: str = "",
    ) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace TEXT NOT NULL,
                kind TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_episodic_ws ON episodic(workspace, created_at);
            CREATE TABLE IF NOT EXISTS semantic (
                workspace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (workspace, key)
            );
            CREATE TABLE IF NOT EXISTS procedural (
                workspace TEXT NOT NULL,
                name TEXT NOT NULL,
                steps TEXT NOT NULL,
                success_count INTEGER NOT NULL DEFAULT 0,
                fail_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (workspace, name)
            );
            """
        )
        self._conn.commit()
        self._gate_llm = gate_llm
        self._gate_model = gate_model

    def close(self) -> None:
        self._conn.close()

    # -- episodic ------------------------------------------------------------

    def remember_event(
        self, workspace: str, kind: str, data: dict[str, Any]
    ) -> MemoryEvent:
        event = MemoryEvent(
            workspace=workspace, kind=kind, data=data, created_at=_now()
        )
        self._conn.execute(
            "INSERT INTO episodic (workspace, kind, data, created_at) VALUES (?,?,?,?)",
            (workspace, kind, json.dumps(data, ensure_ascii=False), event.created_at),
        )
        self._conn.commit()
        return event

    def recent_events(
        self, workspace: str, limit: int = 10
    ) -> list[MemoryEvent]:
        rows = self._conn.execute(
            "SELECT workspace, kind, data, created_at FROM episodic "
            "WHERE workspace=? ORDER BY created_at DESC LIMIT ?",
            (workspace, limit),
        ).fetchall()
        return [
            MemoryEvent(
                workspace=r["workspace"], kind=r["kind"],
                data=json.loads(r["data"]), created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- semantic ------------------------------------------------------------

    def remember_fact(self, workspace: str, key: str, value: str) -> MemoryFact:
        fact = MemoryFact(workspace=workspace, key=key, value=value, updated_at=_now())
        self._conn.execute(
            "INSERT INTO semantic (workspace, key, value, updated_at) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(workspace, key) DO UPDATE SET "
            "value=excluded.value, updated_at=excluded.updated_at",
            (workspace, key, value, fact.updated_at),
        )
        self._conn.commit()
        return fact

    def facts(self, workspace: str) -> list[MemoryFact]:
        rows = self._conn.execute(
            "SELECT workspace, key, value, updated_at FROM semantic "
            "WHERE workspace=? ORDER BY updated_at DESC",
            (workspace,),
        ).fetchall()
        return [
            MemoryFact(
                workspace=r["workspace"], key=r["key"], value=r["value"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    # -- procedural ----------------------------------------------------------

    def learn_procedure(
        self, workspace: str, name: str, steps: tuple[str, ...]
    ) -> Procedure:
        self._conn.execute(
            "INSERT INTO procedural (workspace, name, steps) VALUES (?,?,?) "
            "ON CONFLICT(workspace, name) DO UPDATE SET steps=excluded.steps",
            (workspace, name, json.dumps(list(steps), ensure_ascii=False)),
        )
        self._conn.commit()
        return Procedure(workspace=workspace, name=name, steps=steps)

    def record_outcome(self, workspace: str, name: str, *, success: bool) -> None:
        col = "success_count" if success else "fail_count"
        self._conn.execute(
            f"UPDATE procedural SET {col} = {col} + 1 "
            "WHERE workspace=? AND name=?",
            (workspace, name),
        )
        self._conn.commit()

    def procedures(self, workspace: str) -> list[Procedure]:
        rows = self._conn.execute(
            "SELECT workspace, name, steps, success_count, fail_count "
            "FROM procedural WHERE workspace=? ORDER BY name",
            (workspace,),
        ).fetchall()
        return [
            Procedure(
                workspace=r["workspace"], name=r["name"],
                steps=tuple(json.loads(r["steps"])),
                success_count=r["success_count"], fail_count=r["fail_count"],
            )
            for r in rows
        ]

    # -- retrieval gate (fail-open) ------------------------------------------

    def should_retrieve(self, message: str) -> tuple[bool, str]:
        """Decide whether THIS message needs memory. Fails open to retrieve."""
        # 1) deterministic local gate — no LLM, always available
        lowered = message.lower()
        hits = [k for k in _RETRIEVAL_KEYWORDS if k in lowered]
        if hits:
            return True, " ".join(hits[:6])
        # 2) optional LLM gate for the rest (cheap model), fail-open
        if self._gate_llm is not None:
            try:
                text = self._gate_llm.complete(
                    [{"role": "user", "content": _GATE_PROMPT.format(message=message)}]
                )
                if "{" in text:
                    import json as _json

                    decision = _json.loads(
                        text[text.index("{") : text.rindex("}") + 1]
                    )
                    return bool(decision.get("retrieve")), str(
                        decision.get("query", message)
                    )
            except Exception:  # noqa: BLE001 - gate fails open
                pass
        # 3) default: no business keywords, no gate → no retrieval
        return False, ""

    # -- the combined recall -------------------------------------------------

    def recollect(
        self,
        message: str,
        workspace: str,
        *,
        event_limit: int = 5,
        fact_limit: int = 10,
    ) -> dict[str, Any]:
        """Memory-aware context pack for a message (after the gate says yes)."""
        should, query = self.should_retrieve(message)
        if not should:
            return {"retrieved": False, "query": ""}
        events = self.recent_events(workspace, limit=event_limit)
        facts = self.facts(workspace)[:fact_limit]
        procs = self.procedures(workspace)
        return {
            "retrieved": True,
            "query": query,
            "events": [e.as_dict() for e in events],
            "facts": [f.as_dict() for f in facts],
            "procedures": [p.as_dict() for p in procs],
        }

    def context_block(
        self, message: str, workspace: str
    ) -> str:
        """Markdown context block to inject into a prompt (empty if no recall)."""
        pack = self.recollect(message, workspace)
        if not pack["retrieved"]:
            return ""
        lines = ["## Memory (retrieved by gate)"]
        if pack["facts"]:
            lines.append("### Facts")
            lines += [f"- {f['key']}: {f['value']}" for f in pack["facts"]]
        if pack["events"]:
            lines.append("### Recent events")
            lines += [
                f"- [{e['created_at']}] {e['kind']}: {json.dumps(e['data'], ensure_ascii=False)[:120]}"
                for e in pack["events"]
            ]
        if pack["procedures"]:
            lines.append("### Procedures")
            lines += [
                f"- {p['name']} (ok={p['success_count']}, fail={p['fail_count']})"
                for p in pack["procedures"]
            ]
        return "\n".join(lines)
