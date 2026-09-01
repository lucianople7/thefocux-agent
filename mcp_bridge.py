"""THE FOCUX MCP bridge — the DNA reachable from any MCP host (incl. Codex).

Exposes the FOCUX runtime as MCP tools over stdio (JSON-RPC 2.0), so Codex
(or Claude Code, Cursor, OpenClaw...) can consult the deterministic DNA:

- focux_gate: decide an action (ALLOW/REVIEW/DENY) through the money-gate
- focux_skills: list the mounted skills
- focux_memory: recall business facts/events for a workspace
- focux_learn: crystallize a procedure as a DRAFT skill (human-gated)
- focux_redact: redact secrets from a text (audit hygiene)

Zero external dependencies (stdlib only). Run:
    python mcp_bridge.py            # stdio JSON-RPC (MCP over stdin/stdout)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from focux import build_agent, default_gate  # noqa: E402
from policy.money_gate import Action, ActionClass  # noqa: E402
from runtime.redact import redact_json, redact_mapping  # noqa: E402
from runtime.skills import crystallize_skill, list_drafts  # noqa: E402

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_gate(args: dict) -> dict:
    agent = _get_agent()
    pillar = str(args.get("pillar", "content"))
    objective = str(args.get("objective", ""))
    amount = float(args.get("amount", 0.0) or 0.0)
    target = str(args.get("target", ""))
    result = agent.propose(
        pillar=pillar, objective=objective, amount=amount, target=target,
    )
    # Convention: decisions are UPPERCASE strings system-wide (CLI, webui,
    # FocuxResult). The MCP surface matches them.
    return {"decision": str(result.decision), "summary": result.summary}


def _tool_skills(args: dict) -> dict:
    agent = _get_agent()
    return {
        "skills": [s.name for s in agent.skills],
        "count": len(agent.skills),
    }


def _tool_memory(args: dict) -> dict:
    agent = _get_agent()
    mem = agent.memory
    if mem is None:
        return {"facts": [], "events": [], "procedures": []}
    workspace = str(args.get("workspace", agent.workspace))
    return {
        "facts": [f.as_dict() for f in mem.facts(workspace)],
        "events": [e.as_dict() for e in mem.recent_events(workspace)],
        "procedures": [p.as_dict() for p in mem.procedures(workspace)],
    }


def _tool_learn(args: dict) -> dict:
    agent = _get_agent()
    name = str(args.get("name", "")).strip()
    steps = tuple(str(s) for s in args.get("steps", []) if str(s).strip())
    if not name or not steps:
        return {"error": "name and steps are required"}
    description = str(args.get("description", ""))
    return agent.learn(name, steps, description=description)


def _tool_redact(args: dict) -> dict:
    text = str(args.get("text", ""))
    return {"redacted": redact_json(text) if text.strip().startswith("{")
            else _redact_text(text)}


def _redact_text(text: str) -> str:
    from runtime.redact import redact_text as rt
    return rt(text)


def _tool_survival(args: dict) -> dict:
    """Business survival tier (effort, never authorization)."""
    from runtime.survival import BusinessFinances, report

    finances = BusinessFinances(
        revenue=float(args.get("revenue", 0.0) or 0.0),
        operating_cost=float(args.get("operating_cost", 0.0) or 0.0),
        cash=float(args.get("cash", 0.0) or 0.0),
    )
    return report(finances)


def _tool_heartbeat(args: dict) -> dict:
    """Heartbeat: tier + roles due + next schedule + approvals."""
    from runtime.heartbeat import heartbeat
    from runtime.survival import BusinessFinances

    finances = BusinessFinances(
        revenue=float(args.get("revenue", 0.0) or 0.0),
        operating_cost=float(args.get("operating_cost", 0.0) or 0.0),
        cash=float(args.get("cash", 0.0) or 0.0),
    )
    hb = heartbeat(
        finances,
        pending_approvals=int(args.get("pending_approvals", 0) or 0),
    )
    return hb.as_dict()


def _tool_roles(args: dict) -> dict:
    """List the specialized business roles with schedules (honest count)."""
    from runtime.orchestrator import all_roles

    roles = all_roles()
    return {"roles": [r.as_dict() for r in roles], "count": len(roles)}


def _tool_signals(args: dict) -> dict:
    """Latest absorbed REAL data (github/huggingface/x) as fact lines.

    Reads the repo's shared SQLite memory; empty when nothing absorbed yet
    (run `focux absorb` first).
    """
    from runtime.ingest import recent_signals
    from runtime.memory import FocuxMemory

    db = REPO / "memory" / "focux.db"
    if not db.exists():
        return {"signals": [], "source": "no shared memory yet - run 'focux absorb'"}
    workspace = str(args.get("workspace", "default"))
    mem = FocuxMemory(db)
    try:
        return {
            "workspace": workspace,
            "signals": recent_signals(mem, workspace),
        }
    finally:
        mem.close()


def _tool_focus(args: dict) -> dict:
    """Directed intelligence: OUR real goals + gaps, evidence, work state.

    Call this at session start: the pack tells the agent what to be smart
    ABOUT (the active objectives) and what evidence exists. Empty objectives
    are reported honestly - intelligence without goals is noise.
    """
    from runtime.focus import focus_pack
    from runtime.memory import FocuxMemory

    db = REPO / "memory" / "focux.db"
    if not db.exists():
        return {"workspace": "default", "objectives": [], "signals": [],
                "work": "", "tier": "", "note": "no shared memory yet"}
    workspace = str(args.get("workspace", "default"))
    mem = FocuxMemory(db)
    try:
        return focus_pack(mem, workspace).as_dict()
    finally:
        mem.close()


# ---------------------------------------------------------------------------
# Full intelligence surface over MCP (fluent agent usage)
# ---------------------------------------------------------------------------

def _memory():
    """Repo's shared SQLite memory (created on first use)."""
    from runtime.memory import FocuxMemory

    return FocuxMemory(REPO / "memory" / "focux.db")


def _tool_objective_add(args: dict) -> dict:
    mem = _memory()
    try:
        obj = mem.add_objective(
            str(args.get("workspace", "default")),
            str(args.get("title", "")),
            str(args.get("kpi", "")),
            float(args.get("target", 0)),
            unit=str(args.get("unit", "") or ""),
            deadline=str(args.get("deadline", "") or ""),
        )
        return obj.as_dict()
    finally:
        mem.close()


def _tool_objective_set(args: dict) -> dict:
    mem = _memory()
    try:
        obj = mem.update_objective_current(
            str(args.get("workspace", "default")),
            str(args.get("id", "")),
            float(args.get("current", 0)),
        )
        if obj is None:
            return {"error": f"no objective '{args.get('id')}'"}
        return obj.as_dict()
    finally:
        mem.close()


def _tool_objective_status(args: dict) -> dict:
    from runtime.objectives import objective_status

    mem = _memory()
    try:
        statuses = objective_status(mem, str(args.get("workspace", "default")))
        return {"statuses": [s.as_dict() for s in statuses]}
    finally:
        mem.close()


def _tool_drive(args: dict) -> dict:
    from runtime.objectives import drive

    agent = _get_agent()
    report = drive(
        agent,
        str(args.get("workspace", "default")),
        objective_id=str(args.get("objective_id", "") or ""),
        limit=int(args.get("limit", 3) or 3),
        tier=str(args.get("tier", "normal") or "normal"),
    )
    return report.as_dict()


def _tool_expert_ask(args: dict) -> dict:
    from runtime.experts import ask_expert

    agent = _get_agent()
    answer = ask_expert(
        agent, str(args.get("domain", "")),
        str(args.get("question", "")),
        str(args.get("workspace", "default")),
    )
    return answer.as_dict()


def _tool_expert_review(args: dict) -> dict:
    from runtime.experts import review_draft

    agent = _get_agent()
    verdict = review_draft(
        agent, str(args.get("domain", "")),
        str(args.get("draft", "")),
        str(args.get("workspace", "default")),
    )
    return verdict.as_dict()


def _tool_work_status(args: dict) -> dict:
    from runtime.workflow import load_state, resume_text, status_text, work_root

    root = work_root()
    state = load_state(root)
    return {
        "status": status_text(root),
        "resume": resume_text(root),
        "state": state.as_dict() if state else None,
    }


def _tool_absorb(args: dict) -> dict:
    import os

    from runtime.ingest import absorb, store_results

    workspace = str(args.get("workspace", "default"))
    sources = tuple(
        s.strip() for s in str(args.get("sources", "github,huggingface")).split(",")
        if s.strip()
    )
    results = absorb(
        sources=sources,
        github_query=str(args.get("query", "ai agent")),
        x_bearer=os.environ.get("X_BEARER_TOKEN", ""),
        x_query=str(args.get("query", "ai agent")),
        limit=int(args.get("limit", 5) or 5),
    )
    mem = _memory()
    try:
        stored = store_results(results, mem, workspace=workspace)
    finally:
        mem.close()
    return {
        "stored": stored,
        "workspace": workspace,
        "sources": {s: {"ok": r.ok, "error": r.error,
                        "items": list(r.items)} for s, r in results.items()},
    }


# ---------------------------------------------------------------------------
# Project graph over MCP (deterministic, local)
# ---------------------------------------------------------------------------

_graph_cache: dict = {}


def _project_graph():
    """The mapped project graph (.focux/map/projectmap.json), cached."""
    from runtime.projectmap import load_graph

    if "graph" not in _graph_cache:
        path = REPO / ".focux" / "map" / "projectmap.json"
        if not path.exists():
            _graph_cache["graph"] = None
        else:
            _graph_cache["graph"] = load_graph(path)
    return _graph_cache["graph"]


def _tool_graph_explain(args: dict) -> dict:
    from runtime.projectmap import explain

    graph = _project_graph()
    if graph is None:
        return {"found": False, "reason": "no map yet - run `focux map`"}
    return explain(graph, str(args.get("name", "")))


def _tool_graph_path(args: dict) -> dict:
    from runtime.projectmap import shortest_path

    graph = _project_graph()
    if graph is None:
        return {"found": False, "reason": "no map yet - run `focux map`"}
    return shortest_path(graph, str(args.get("a", "")), str(args.get("b", "")))


def _tool_graph_query(args: dict) -> dict:
    from runtime.projectmap import query

    graph = _project_graph()
    if graph is None:
        return {"nodes": [], "edges": [], "matched": 0,
                "reason": "no map yet - run `focux map`"}
    return query(graph, str(args.get("question", "")),
                 limit=int(args.get("limit", 8) or 8))


def _tool_selfmod(args: dict) -> dict:
    """Append-only self-modification audit (skills crystallized, etc.)."""
    from runtime.selfmod import SelfModLog, is_protected

    path = str(args.get("path", "memory/selfmod.jsonl"))
    log = SelfModLog(path)
    kind = str(args.get("kind", "")) or None
    return {
        "entries": [e.as_dict() for e in log.entries(limit=20)],
        "count": log.count(kind),
        "protected": list(
            p for p in ("constitution.md", "policy/money_gate.py", "AGENTS.md")
            if is_protected(p)
        ),
    }


# ---------------------------------------------------------------------------
# Tool registry (MCP-style)
# ---------------------------------------------------------------------------

TOOLS: dict[str, dict] = {
    "focux_gate": {
        "description": "THE FOCUX money-gate: decide an action (ALLOW/REVIEW/DENY). "
                       "Call BEFORE any money/publish/account action.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pillar": {"type": "string", "description": "content|commerce|monetization|research|account"},
                "objective": {"type": "string", "description": "what the action does"},
                "amount": {"type": "number", "description": "amount if any"},
                "target": {"type": "string", "description": "recipient/endpoint"},
            },
            "required": ["objective"],
        },
        "handler": _tool_gate,
    },
    "focux_skills": {
        "description": "List the THE FOCUX skills mounted in this environment.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_skills,
    },
    "focux_memory": {
        "description": "Recall business memory (facts, events, procedures) for a workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
        },
        "handler": _tool_memory,
    },
    "focux_learn": {
        "description": "Crystallize an executed procedure as a DRAFT skill (human review required before activation).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "steps": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "string"},
            },
            "required": ["name", "steps"],
        },
        "handler": _tool_learn,
    },
    "focux_redact": {
        "description": "Redact secrets (API keys, tokens) from text or JSON before logging.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "handler": _tool_redact,
    },
    "focux_survival": {
        "description": "Business survival tier from revenue/cost/cash. Changes EFFORT, never authorization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "revenue": {"type": "number", "description": "trailing revenue"},
                "operating_cost": {"type": "number", "description": "trailing cost"},
                "cash": {"type": "number", "description": "buffer"},
            },
        },
        "handler": _tool_survival,
    },
    "focux_heartbeat": {
        "description": "Heartbeat: survival tier + roles due now + next schedule + pending approvals.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "revenue": {"type": "number"},
                "operating_cost": {"type": "number"},
                "cash": {"type": "number"},
                "pending_approvals": {"type": "integer"},
            },
        },
        "handler": _tool_heartbeat,
    },
    "focux_roles": {
        "description": "List the specialized business roles with schedules (orchestrator, planning, social, finance, evolution...).",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_roles,
    },
    "focux_signals": {
        "description": "Latest absorbed REAL data (github/huggingface/x) as fact lines for analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string", "description": "workspace to read (default)"},
            },
        },
        "handler": _tool_signals,
    },
    "focux_focus": {
        "description": "Directed intelligence at session start: OUR real goals + gaps, evidence, work state. Be smart ONLY about these.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string", "description": "workspace (default)"},
            },
        },
        "handler": _tool_focus,
    },
    "focux_objective_add": {
        "description": "Add a measurable objective the brain drives toward.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"}, "kpi": {"type": "string"},
                "target": {"type": "number"}, "unit": {"type": "string"},
                "deadline": {"type": "string"},
                "workspace": {"type": "string"},
            },
            "required": ["title", "kpi", "target"],
        },
        "handler": _tool_objective_add,
    },
    "focux_objective_set": {
        "description": "MEDIR: record a measured KPI value for an objective.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"}, "current": {"type": "number"},
                "workspace": {"type": "string"},
            },
            "required": ["id", "current"],
        },
        "handler": _tool_objective_set,
    },
    "focux_objective_status": {
        "description": "Where each objective stands: progress, gap, overdue, momentum.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
        },
        "handler": _tool_objective_status,
    },
    "focux_drive": {
        "description": "INTELLIGENCE pass: gap analysis + real signals -> gated action plan (LLM proposes, gate decides, never auto-authorizes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective_id": {"type": "string"}, "limit": {"type": "integer"},
                "tier": {"type": "string"}, "workspace": {"type": "string"},
            },
        },
        "handler": _tool_drive,
    },
    "focux_expert_ask": {
        "description": "Consult a world-class domain expert (content/social/ecommerce/monetization/opportunities), grounded in playbook + real signals.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"}, "question": {"type": "string"},
                "workspace": {"type": "string"},
            },
            "required": ["domain", "question"],
        },
        "handler": _tool_expert_ask,
    },
    "focux_expert_review": {
        "description": "Quality gate: PASS/REVISE a draft against the domain checklist (hook, offer, price, validation...).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"}, "draft": {"type": "string"},
                "workspace": {"type": "string"},
            },
            "required": ["domain", "draft"],
        },
        "handler": _tool_expert_review,
    },
    "focux_work_status": {
        "description": "Work Harness state: where the current stage-gated work stands + resume info.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "handler": _tool_work_status,
    },
    "focux_absorb": {
        "description": "Absorb REAL data (github/huggingface/x) into memory as facts for analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sources": {"type": "string"}, "query": {"type": "string"},
                "limit": {"type": "integer"}, "workspace": {"type": "string"},
            },
        },
        "handler": _tool_absorb,
    },
    "focux_graph_explain": {
        "description": "A concept in the mapped project graph and its connections (EXTRACTED vs INFERRED).",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "handler": _tool_graph_explain,
    },
    "focux_graph_path": {
        "description": "Shortest path between two concepts in the project graph (hop by hop).",
        "inputSchema": {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
            "required": ["a", "b"],
        },
        "handler": _tool_graph_path,
    },
    "focux_graph_query": {
        "description": "Keyword-scored subgraph for a plain-language question (deterministic, local).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"}, "limit": {"type": "integer"},
            },
            "required": ["question"],
        },
        "handler": _tool_graph_query,
    },
    "focux_selfmod": {
        "description": "Append-only self-modification audit (skills crystallized, drafts). Protected files listed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "description": "filter by kind"},
                "path": {"type": "string", "description": "audit log path"},
            },
        },
        "handler": _tool_selfmod,
    },
}


# ---------------------------------------------------------------------------
# MCP stdio server (JSON-RPC 2.0)
# ---------------------------------------------------------------------------

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _handle(msg: dict, tools_list: list[dict]) -> dict | None:
    """Handle one JSON-RPC message; returns the response (None for notif)."""
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "thefocux-dna", "version": "1.0.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        meta = TOOLS.get(name)
        if meta is None:
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        try:
            result = meta["handler"](args)
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
                    ],
                },
            }
        except Exception as exc:  # noqa: BLE001 - report tool failure
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"},
            }
    return {
        "jsonrpc": "2.0", "id": msg_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def _tools_list() -> list[dict]:
    return [
        {
            "name": name,
            "description": meta["description"],
            "inputSchema": meta["inputSchema"],
        }
        for name, meta in TOOLS.items()
    ]


def selfcheck() -> int:
    """In-process handshake: initialize + tools/list + gate call (READ).

    Used by `focux doctor` to prove the MCP surface answers over stdio
    without needing a live MCP host.
    """
    tools = _tools_list()
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "focux_gate",
                    "arguments": {"pillar": "research", "objective": "selfcheck"}}},
    ]
    try:
        responses = {}
        for m in msgs:
            r = _handle(m, tools)
            if r is not None:
                responses[m["id"]] = r
        listed = responses[2]["result"]["tools"]
        gate_text = responses[3]["result"]["content"][0]["text"]
        gate = json.loads(gate_text)
        decision = gate.get("decision", "?")
        if decision not in ("ALLOW", "REVIEW", "DENY"):
            raise ValueError(f"unexpected decision: {decision!r}")
        print(f"MCP OK: {len(listed)} tools; gate(research/read) -> {decision}")
        return 0
    except Exception as exc:  # noqa: BLE001 - selfcheck failure
        print(f"MCP FAIL: {type(exc).__name__}: {exc}")
        return 1


def main() -> int:
    tools_list = _tools_list()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(msg, tools_list)
        if resp is not None:
            _send(resp)
    return 0


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        raise SystemExit(selfcheck())
    raise SystemExit(main())
