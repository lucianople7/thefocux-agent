"""Tests for the FOCUX web console — zero-dependency local WebUI."""
from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from webui import Handler, main  # noqa: E402

PORT = 3199


@pytest.fixture(scope="module")
def server():
    from http.server import ThreadingHTTPServer

    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()


def _get(path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10) as resp:  # noqa: S310
        return resp.status, resp.read()


def _post(path: str, body: dict):
    req = urllib.request.Request(  # noqa: S310
        f"http://127.0.0.1:{PORT}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # urlopen raises on 4xx/5xx; tests assert on the status.
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_console_serves_html(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/")
    assert status == 200
    assert b"THE FOCUX Agent" in body
    assert b"focux" in body.lower() or b"FOCUX" in body


def test_logo_served(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/api/logo")
    assert status == 200
    assert body[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic


def test_status(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/api/status")
    data = json.loads(body)
    assert status == 200
    assert data["skills"] >= 17
    assert data["gate"] == "money-gate activo"


def test_skills_endpoint(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/api/skills")
    data = json.loads(body)
    assert status == 200
    assert len(data["skills"]) >= 17


def test_chat_returns_gate_decision(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _post("/api/chat", {"message": "publica un post sobre IA", "pillar": "content"})
    assert status == 200
    assert data["decision"] in ("ALLOW", "REVIEW", "DENY")


def test_tool_gate_review(server) -> None:  # type: ignore[no-untyped-def]
    status, data = _post("/api/tool", {"tool": "make_payment", "args": {"amount": 50, "to": "ads"}})
    assert status == 200
    assert data["decision"] == "REVIEW"
    assert data["idempotency_key"]


def test_tool_card_never_leaks_secrets(server) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION (round 10): approval card must never embed secrets."""
    secret = "sk-live-ULTRAHIDDENsecret987"
    status, data = _post("/api/tool", {
        "tool": "update_credentials",
        "args": {"target": "stripe", "secret": secret},
    })
    assert status == 200
    assert data["decision"] == "REVIEW"
    blob = str(data)
    assert secret not in blob
    assert "<redacted" in blob or "redacted" in blob


def test_approve_flow(server) -> None:  # type: ignore[no-untyped-def]
    _, tool = _post("/api/tool", {"tool": "create_listing", "args": {"product": "ebook", "price": 19}})
    key = tool["idempotency_key"]
    status, data = _post("/api/approve", {"idempotency_key": key})
    assert status == 200
    assert "aprobado" in data["message"]
    # second approve: no pending card
    status2, data2 = _post("/api/approve", {"idempotency_key": key})
    assert status2 == 404


def test_memory_endpoint(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/api/memory?workspace=default")
    data = json.loads(body)
    assert status == 200
    assert "facts" in data and "events" in data and "procedures" in data


def test_drafts_endpoint(server) -> None:  # type: ignore[no-untyped-def]
    status, body = _get("/api/drafts")
    data = json.loads(body)
    assert status == 200
    assert "drafts" in data


def test_unknown_route_404(server) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(Exception):
        _get("/api/nope")
