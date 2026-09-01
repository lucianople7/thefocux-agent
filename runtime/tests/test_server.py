"""Tests for THE FOCUX SERVER: the brain as a service over HTTP."""
from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.server import Handler  # noqa: E402


@pytest.fixture()
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()


def _get(server, path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{server.server_port}{path}", timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post(server, path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(  # noqa: S310
        f"http://127.0.0.1:{server.server_port}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_landing_served(server) -> None:  # type: ignore[no-untyped-def]
    with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{server.server_port}/", timeout=30) as resp:
        body = resp.read().decode("utf-8")
    assert resp.status == 200
    assert "THE FOCUX BRAIN" in body
    assert "/status" in body


def test_status_endpoint(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _get(server, "/status")
    assert status == 200
    assert "objectives" in data
    assert "tier" in data


def test_focus_endpoint(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _get(server, "/focus")
    assert status == 200
    assert "objectives" in data


def test_gate_endpoint_never_autoapproves_money(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _post(server, "/gate", {
        "pillar": "monetization", "objective": "payout", "amount": 100})
    assert status == 200
    assert data["decision"] == "REVIEW"


def test_mcp_passthrough_over_http(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _post(server, "/mcp", {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}}})
    assert status == 200
    assert data["result"]["serverInfo"]["name"] == "thefocux-dna"
    status2, data2 = _post(server, "/mcp", {
        "jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert status2 == 200
    names = {t["name"] for t in data2["result"]["tools"]}
    assert "focux_gate" in names
    assert "focux_graph_path" in names  # 22 tools reachable over HTTP


def test_unknown_route_404(server) -> None:  # type: ignore[no-untyped-def]
    try:
        _get(server, "/nope")
        assert False, "should 404"
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_cors_headers(server) -> None:  # type: ignore[no-untyped-def]
    with urllib.request.urlopen(  # noqa: S310
            f"http://127.0.0.1:{server.server_port}/status", timeout=30) as resp:
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
