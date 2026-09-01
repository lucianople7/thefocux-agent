"""E2E test for the FOCUX MCP bridge — the DNA reachable from Codex/MCP hosts."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def _run_mcp(messages: list[dict]) -> list[dict]:
    lines = [json.dumps(m) for m in messages]
    proc = subprocess.run(
        [sys.executable, "mcp_bridge.py"],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def test_initialize() -> None:
    out = _run_mcp([{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2024-11-05", "capabilities": {}}}])
    assert out[0]["result"]["serverInfo"]["name"] == "thefocux-dna"
    assert "tools" in out[0]["result"]["capabilities"]


def test_tools_list() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    result = out[-1]["result"]
    names = [t["name"] for t in result["tools"]]
    assert "focux_gate" in names
    assert "focux_skills" in names
    assert "focux_memory" in names
    assert "focux_learn" in names
    assert "focux_redact" in names
    assert "focux_survival" in names
    assert "focux_heartbeat" in names
    assert "focux_roles" in names
    assert "focux_selfmod" in names


def test_survival_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_survival",
                    "arguments": {"revenue": 1000, "operating_cost": 900, "cash": 5000}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "tier" in data
    assert data["authorization_unchanged"] is True


def test_heartbeat_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_heartbeat",
                    "arguments": {"revenue": 1000, "operating_cost": 900, "cash": 5000,
                                  "pending_approvals": 2}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "tier" in data
    assert "roles_due" in data
    assert data["pending_approvals"] == 2


def test_roles_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_roles", "arguments": {}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    # Honest count: matches the roles actually returned (never a hardcoded lie).
    assert data["count"] == len(data["roles"])
    assert data["count"] >= 11


def test_signals_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_signals", "arguments": {"workspace": "research"}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "signals" in data
    assert isinstance(data["signals"], list)


def test_selfcheck_mode() -> None:
    proc = subprocess.run(
        [sys.executable, "mcp_bridge.py", "--selfcheck"],
        capture_output=True, text=True, cwd=str(REPO), timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "MCP OK" in proc.stdout
    assert "gate(research/read)" in proc.stdout


def test_selfmod_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_selfmod", "arguments": {}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "entries" in data
    assert "protected" in data
    assert "constitution.md" in data["protected"]


def test_gate_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_gate",
                    "arguments": {"pillar": "monetization", "objective": "payout", "amount": 100}}},
    ])
    result = out[-1]["result"]
    text = result["content"][0]["text"]
    data = json.loads(text)
    assert data["decision"] in ("ALLOW", "REVIEW", "DENY")


def test_skills_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_skills", "arguments": {}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert data["count"] >= 17


def test_redact_tool() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_redact",
                    "arguments": {"text": '{"api_key": "sk-abcdefghijklmnop", "topic": "AI"}'}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "sk-abcdefghijklmnop" not in data["redacted"]


def test_unknown_tool_error() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "nope", "arguments": {}}},
    ])
    assert "error" in out[-1]


def test_learn_tool_crystallizes_draft(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # learn tool requires drafts_dir on the agent; default agent has none, so
    # it returns learned=False gracefully rather than crashing.
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "focux_learn",
                    "arguments": {"name": "x", "steps": ["a", "b"]}}},
    ])
    data = json.loads(out[-1]["result"]["content"][0]["text"])
    assert "learned" in data  # False gracefully when no drafts_dir


def _call_tool(name: str, arguments: dict) -> dict:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}},
    ])
    return json.loads(out[-1]["result"]["content"][0]["text"])


def test_objective_add_status_mcp() -> None:
    """The full objective surface is reachable over MCP (agent fluency)."""
    ws = "mcp-test"
    added = _call_tool("focux_objective_add", {
        "workspace": ws, "title": "MCP meta", "kpi": "leads",
        "target": 50, "deadline": "2026-12-31"})
    assert added["objective_id"] == "mcp-meta"
    status = _call_tool("focux_objective_status", {"workspace": ws})
    assert any(o["objective_id"] == "mcp-meta" for o in status["statuses"])
    measured = _call_tool("focux_objective_set", {
        "workspace": ws, "id": "mcp-meta", "current": 25})
    assert measured["current"] == 25
    status2 = _call_tool("focux_objective_status", {"workspace": ws})
    meta = [o for o in status2["statuses"] if o["objective_id"] == "mcp-meta"][0]
    assert meta["progress"] == 0.5


def test_work_status_mcp() -> None:
    data = _call_tool("focux_work_status", {})
    assert "status" in data
    assert "resume" in data
    assert "state" in data


def test_new_intelligence_tools_listed() -> None:
    out = _run_mcp([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    names = {t["name"] for t in out[-1]["result"]["tools"]}
    for expected in ("focux_objective_add", "focux_objective_set",
                     "focux_objective_status", "focux_drive",
                     "focux_expert_ask", "focux_expert_review",
                     "focux_work_status", "focux_absorb"):
        assert expected in names
