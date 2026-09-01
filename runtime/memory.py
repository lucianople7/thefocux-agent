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
import threading
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
    # identity / mission / strategy triggers (BRAIN self-improvement: found by
    # live test 2026-08-31 — "north star" queries missed the gate)
    "north star", "northstar", "misión", "mision", "misio", "objetivo",
    "objective", "estrategia", "strategy", "quién soy", "who am i", "identidad",
    "identity", "metas", "goals", "proposito", "purpose", "vision", "visión",
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


@dataclass(frozen=True)
class Objective:
    """A measurable business objective the brain drives toward.

    ``kpi`` names the metric (followers, revenue, leads, pieces...),
    ``target`` the goal, ``current`` the measured value (updated by the
    operator or by MEDIR), ``deadline`` an ISO date. ``plan`` holds the
    last gated action plan the intelligence pass proposed.
    """

    workspace: str
    objective_id: str
    title: str
    kpi: str
    target: float
    current: float = 0.0
    unit: str = ""
    deadline: str = ""
    created_at: str = ""
    plan: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "workspace": self.workspace,
            "objective_id": self.objective_id,
            "title": self.title,
            "kpi": self.kpi,
            "target": self.target,
            "current": self.current,
            "unit": self.unit,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "plan": list(self.plan),
        }

    def progress(self) -> float:
        """0.0..1.0 (capped); 1.0 when achieved; 0.0 for zero targets."""
        if self.target <= 0:
            return 1.0
        return max(0.0, min(1.0, self.current / self.target))


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _objective_id(title: str) -> str:
    """Stable slug from the title (kebab-case, ascii) for objective ids."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:48] or "objective"


def _row_to_objective(row) -> Objective:  # type: ignore[no-untyped-def]
    return Objective(
        workspace=row["workspace"], objective_id=row["objective_id"],
        title=row["title"], kpi=row["kpi"], target=float(row["target"]),
        current=float(row["current"]), unit=row["unit"], deadline=row["deadline"],
        created_at=row["created_at"],
        plan=tuple(json.loads(row["plan"] or "[]")),
    )


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
        # check_same_thread=False: the memory is served by threaded hosts
        # (webui ThreadingHTTPServer, MCP hosts) that build the agent in one
        # worker thread and query it in another. A lock serializes all DB
        # access so interleaved execute/commit sequences can never corrupt.
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
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
                CREATE TABLE IF NOT EXISTS objectives (
                    workspace TEXT NOT NULL,
                    objective_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    kpi TEXT NOT NULL,
                    target REAL NOT NULL,
                    current REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT '',
                    deadline TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT '[]',
                    PRIMARY KEY (workspace, objective_id)
                );
                CREATE TABLE IF NOT EXISTS objective_history (
                    objective_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    current REAL NOT NULL
                );
                """
            )
            self._conn.commit()
        self._gate_llm = gate_llm
        self._gate_model = gate_model

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # -- episodic ------------------------------------------------------------

    def remember_event(
        self, workspace: str, kind: str, data: dict[str, Any]
    ) -> MemoryEvent:
        event = MemoryEvent(
            workspace=workspace, kind=kind, data=data, created_at=_now()
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO episodic (workspace, kind, data, created_at) VALUES (?,?,?,?)",
                (workspace, kind, json.dumps(data, ensure_ascii=False), event.created_at),
            )
            self._conn.commit()
        return event

    def recent_events(
        self, workspace: str, limit: int = 10
    ) -> list[MemoryEvent]:
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            self._conn.execute(
                "INSERT INTO procedural (workspace, name, steps) VALUES (?,?,?) "
                "ON CONFLICT(workspace, name) DO UPDATE SET steps=excluded.steps",
                (workspace, name, json.dumps(list(steps), ensure_ascii=False)),
            )
            self._conn.commit()
        return Procedure(workspace=workspace, name=name, steps=steps)

    def record_outcome(self, workspace: str, name: str, *, success: bool) -> None:
        col = "success_count" if success else "fail_count"
        with self._lock:
            self._conn.execute(
                f"UPDATE procedural SET {col} = {col} + 1 "
                "WHERE workspace=? AND name=?",
                (workspace, name),
            )
            self._conn.commit()

    def procedures(self, workspace: str) -> list[Procedure]:
        with self._lock:
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

    # -- objectives (the brain drives toward measurable goals) ---------------

    def add_objective(
        self,
        workspace: str,
        title: str,
        kpi: str,
        target: float,
        *,
        unit: str = "",
        deadline: str = "",
    ) -> Objective:
        objective_id = _objective_id(title)
        obj = Objective(
            workspace=workspace, objective_id=objective_id, title=title,
            kpi=kpi, target=float(target), unit=unit, deadline=deadline,
            created_at=_now(),
        )
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO objectives "
                "(workspace, objective_id, title, kpi, target, current, unit, "
                " deadline, created_at, plan) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (workspace, objective_id, title, kpi, obj.target, obj.current,
                 unit, deadline, obj.created_at, "[]"),
            )
            self._conn.commit()
        return obj

    def objectives(self, workspace: str) -> list[Objective]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT workspace, objective_id, title, kpi, target, current, "
                "unit, deadline, created_at, plan FROM objectives "
                "WHERE workspace=? ORDER BY created_at",
                (workspace,),
            ).fetchall()
        return [_row_to_objective(r) for r in rows]

    def get_objective(
        self, workspace: str, objective_id: str
    ) -> Objective | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT workspace, objective_id, title, kpi, target, current, "
                "unit, deadline, created_at, plan FROM objectives "
                "WHERE workspace=? AND objective_id=?",
                (workspace, objective_id),
            ).fetchone()
        return _row_to_objective(row) if row else None

    def update_objective_current(
        self, workspace: str, objective_id: str, value: float
    ) -> Objective | None:
        """MEDIR: record a new measured value (keeps history for momentum)."""
        with self._lock:
            self._conn.execute(
                "UPDATE objectives SET current=? "
                "WHERE workspace=? AND objective_id=?",
                (float(value), workspace, objective_id),
            )
            self._conn.execute(
                "INSERT INTO objective_history (objective_id, recorded_at, current) "
                "VALUES (?,?,?)",
                (objective_id, _now(), float(value)),
            )
            self._conn.commit()
        return self.get_objective(workspace, objective_id)

    def set_objective_plan(
        self, workspace: str, objective_id: str, plan: list[dict[str, Any]]
    ) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE objectives SET plan=? WHERE workspace=? AND objective_id=?",
                (json.dumps(plan, ensure_ascii=False), workspace, objective_id),
            )
            self._conn.commit()

    def objective_history(self, objective_id: str) -> list[tuple[str, float]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT recorded_at, current FROM objective_history "
                "WHERE objective_id=? ORDER BY recorded_at",
                (objective_id,),
            ).fetchall()
        return [(r["recorded_at"], float(r["current"])) for r in rows]

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
