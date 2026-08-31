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
    return {"decision": result.decision, "summary": result.summary}


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
}


# ---------------------------------------------------------------------------
# MCP stdio server (JSON-RPC 2.0)
# ---------------------------------------------------------------------------

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> int:
    tools_list = [
        {
            "name": name,
            "description": meta["description"],
            "inputSchema": meta["inputSchema"],
        }
        for name, meta in TOOLS.items()
    ]
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method", "")
        msg_id = msg.get("id")

        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "thefocux-dna", "version": "1.0.0"},
                },
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}})
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name", "")
            args = params.get("arguments", {}) or {}
            meta = TOOLS.get(name)
            if meta is None:
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32602, "message": f"unknown tool: {name}"},
                })
                continue
            try:
                result = meta["handler"](args)
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, ensure_ascii=False)}
                        ],
                    },
                })
            except Exception as exc:  # noqa: BLE001 - report tool failure
                _send({
                    "jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"},
                })
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": msg_id, "result": {}})
        else:
            _send({
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
