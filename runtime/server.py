"""THE FOCUX SERVER — the brain as a service: connect from ANYWHERE easily.

The jewel's connectivity layer: the whole brain over HTTP/JSON with CORS,
so Android apps, web pages, other machines, and any agent can connect with
one URL. Stdlib-only (http.server), zero dependencies.

Endpoints (all JSON, errors as {"error": ...}):
  GET  /              landing + endpoint list
  GET  /status        master status (tier, objectives, work, mcp)
  GET  /focus         directed intelligence pack
  GET  /objectives    objectives with gaps/momentum
  POST /gate          money-gate decision {pillar, objective, amount, target}
  POST /ask           ask anything {question}
  POST /drive         intelligence pass toward objectives
  POST /insights      opportunity analyst
  POST /improve       success governor (improvements at all hours)
  POST /absorb        real data (github/huggingface/x)
  POST /expert/ask    world-class expert {domain, question}
  POST /expert/review quality gate {domain, draft}
  POST /mcp           JSON-RPC passthrough (the 22 MCP tools over HTTP)

Run: `focux serve --host 0.0.0.0 --port 8765` to expose on the LAN for
Android/other machines. `focux link` prints the connection guide.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from focux import REPO_ROOT, build_agent, default_gate
from runtime.master import master_status
from runtime.memory import FocuxMemory


def _agent():
    return build_agent()


def _memory():
    return FocuxMemory(REPO_ROOT / "memory" / "focux.db")


def _obj(body: dict[str, Any], key: str, default: Any = "") -> Any:
    return body.get(key, default)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_status(body: dict) -> dict:
    mem = _memory()
    try:
        return master_status(mem, str(_obj(body, "workspace", "default")))
    finally:
        mem.close()


def handle_focus(body: dict) -> dict:
    from runtime.focus import focus_pack

    mem = _memory()
    try:
        return focus_pack(mem, str(_obj(body, "workspace", "default"))).as_dict()
    finally:
        mem.close()


def handle_objectives(body: dict) -> dict:
    from runtime.objectives import objective_status

    mem = _memory()
    try:
        statuses = objective_status(mem, str(_obj(body, "workspace", "default")))
        return {"statuses": [s.as_dict() for s in statuses]}
    finally:
        mem.close()


def handle_gate(body: dict) -> dict:
    result = _agent().propose(
        pillar=str(_obj(body, "pillar", "content")),
        objective=str(_obj(body, "objective", "")),
        amount=float(_obj(body, "amount", 0) or 0),
        target=str(_obj(body, "target", "") or ""),
    )
    return {"decision": str(result.decision), "summary": result.summary}


def handle_ask(body: dict) -> dict:
    from runtime.ask import ask

    return ask(_agent(), str(_obj(body, "question", "")),
               str(_obj(body, "workspace", "default"))).as_dict()


def handle_drive(body: dict) -> dict:
    from runtime.objectives import drive

    report = drive(
        _agent(), str(_obj(body, "workspace", "default")),
        objective_id=str(_obj(body, "objective_id", "") or ""),
        limit=int(_obj(body, "limit", 3) or 3),
        tier=str(_obj(body, "tier", "normal") or "normal"),
    )
    return report.as_dict()


def handle_insights(body: dict) -> dict:
    from runtime.ask import insights

    return insights(_agent(), str(_obj(body, "workspace", "default")),
                    limit=int(_obj(body, "limit", 3) or 3),
                    tier=str(_obj(body, "tier", "normal") or "normal"))


def handle_improve(body: dict) -> dict:
    from runtime.improve import improve

    return improve(
        _agent(), str(_obj(body, "workspace", "default")),
        system=bool(_obj(body, "system", False)),
        limit=int(_obj(body, "limit", 4) or 4),
        tier=str(_obj(body, "tier", "normal") or "normal"),
        repo_root=REPO_ROOT,
    )


def handle_absorb(body: dict) -> dict:
    from runtime.ingest import absorb, store_results

    workspace = str(_obj(body, "workspace", "default"))
    sources = tuple(
        s.strip() for s in str(_obj(body, "sources", "github,huggingface")).split(",")
        if s.strip())
    results = absorb(
        sources=sources,
        github_query=str(_obj(body, "query", "ai agent")),
        x_bearer=os.environ.get("X_BEARER_TOKEN", ""),
        x_query=str(_obj(body, "query", "ai agent")),
        limit=int(_obj(body, "limit", 5) or 5),
    )
    mem = _memory()
    try:
        stored = store_results(results, mem, workspace=workspace)
    finally:
        mem.close()
    return {"stored": stored, "workspace": workspace,
            "sources": {s: {"ok": r.ok, "error": r.error}
                        for s, r in results.items()}}


def handle_expert_ask(body: dict) -> dict:
    from runtime.experts import ask_expert

    return ask_expert(_agent(), str(_obj(body, "domain", "")),
                      str(_obj(body, "question", "")),
                      str(_obj(body, "workspace", "default"))).as_dict()


def handle_expert_review(body: dict) -> dict:
    from runtime.experts import review_draft

    return review_draft(_agent(), str(_obj(body, "domain", "")),
                        str(_obj(body, "draft", "")),
                        str(_obj(body, "workspace", "default"))).as_dict()


def handle_mcp(body: dict) -> dict:
    """JSON-RPC passthrough: the 22 MCP tools over HTTP."""
    import mcp_bridge

    tools = mcp_bridge._tools_list()
    resp = mcp_bridge._handle(body, tools)
    return resp if resp is not None else {"ok": True}


ROUTES: dict[str, tuple[str, Callable[[dict], dict]]] = {
    "/status": ("GET", handle_status),
    "/focus": ("GET", handle_focus),
    "/objectives": ("GET", handle_objectives),
    "/gate": ("POST", handle_gate),
    "/ask": ("POST", handle_ask),
    "/drive": ("POST", handle_drive),
    "/insights": ("POST", handle_insights),
    "/improve": ("POST", handle_improve),
    "/absorb": ("POST", handle_absorb),
    "/expert/ask": ("POST", handle_expert_ask),
    "/expert/review": ("POST", handle_expert_review),
    "/mcp": ("POST", handle_mcp),
}

LANDING = """<!doctype html><html><head><meta charset="utf-8"><title>THE FOCUX BRAIN</title>
<style>body{font-family:system-ui;background:#0b0e14;color:#e6e9f0;padding:2rem}
h1{color:#e7c46e}.ep{background:#131722;border:1px solid #232a3b;border-radius:8px;
padding:.5rem 1rem;margin:.25rem 0;font-family:monospace}</style></head><body>
<h1>THE FOCUX BRAIN — conectado</h1>
<p>El cerebro esta vivo y responde. Endpoints (JSON, CORS abierto):</p>
{eps}<p><a href="/status">/status</a> es la forma mas rapida de comprobar que todo funciona.</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "thefocux/1.0"

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/":
            eps = "\n".join(
                f'<div class="ep">[{m}] <a href="{p}">{p}</a></div>'
                for p, (m, _) in ROUTES.items())
            body = LANDING.replace("{eps}", eps).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        route = ROUTES.get(path)
        if route is None or route[0] != "GET":
            self._json(404, {"error": f"unknown route: {path}"})
            return
        try:
            self._json(200, route[1]({}))
        except Exception as exc:  # noqa: BLE001 - report, never crash
            self._json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        route = ROUTES.get(path)
        if route is None or route[0] != "POST":
            self._json(404, {"error": f"unknown route: {path}"})
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON body"})
            return
        try:
            self._json(200, route[1](body))
        except Exception as exc:  # noqa: BLE001 - report, never crash
            self._json(500, {"error": f"{type(exc).__name__}: {exc}"})


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Serve the brain over HTTP until interrupted."""
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"THE FOCUX BRAIN serving on http://{host}:{port}")
    print("  GET /status | /focus | /objectives | POST /gate /ask /drive "
          "/insights /improve /absorb /expert/* /mcp")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
