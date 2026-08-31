"""THE FOCUX Agent — local web console (zero dependencies, MIT).

A single-file WebUI over the FOCUX runtime using ONLY the Python standard
library (http.server). It gives the agent its "de serie" face: your logo,
chat with the agent, gated tool approval cards, memory, drafts and skills —
all served from this repo, no external framework, no npm, no Docker.

Endpoints:
  GET  /                       -> the console (logo + panels)
  GET  /api/status             -> agent status (skills, memory, drafts)
  GET  /api/skills             -> loaded skills
  POST /api/chat               -> {message, workspace} -> agent draft
  POST /api/tool               -> {tool, args} -> gated tool request (REVIEW card)
  POST /api/approve            -> {idempotency_key} -> approve a REVIEW card
  GET  /api/memory             -> facts + events + procedures (workspace)
  GET  /api/drafts             -> crystallized drafts
  POST /api/promote            -> {name} -> promote a DRAFT (human step)
  GET  /api/logo               -> THE FOCUX mark

Run:  python webui.py [--port 3080]
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from focux import build_agent, build_llm, default_gate  # noqa: E402
from policy.money_gate import Action, ActionClass, Decision, MoneyGate  # noqa: E402
from runtime.skills import list_drafts, promote_skill  # noqa: E402

# ---------------------------------------------------------------------------
# Agent wiring (same as the CLI: any LLM via env, gates always on)
# ---------------------------------------------------------------------------

_agent = None
_pending: dict[str, dict] = {}  # idempotency_key -> action (REVIEW cards)


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


# ---------------------------------------------------------------------------
# Console HTML (branded)
# ---------------------------------------------------------------------------

CONSOLE_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>THE FOCUX Agent</title>
<style>
  :root { --bg:#0b0e14; --card:#131722; --border:#232a3b; --text:#e6e9f0;
          --muted:#8b93a7; --accent:#e7c46e; --ok:#3ddc84; --warn:#ffb454; --bad:#ff6b6b; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:system-ui,Segoe UI,Roboto,sans-serif; background:var(--bg); color:var(--text); }
  header { display:flex; align-items:center; gap:14px; padding:14px 22px; border-bottom:1px solid var(--border); }
  header img { height:44px; width:44px; object-fit:contain; border-radius:10px; }
  header h1 { font-size:18px; margin:0; letter-spacing:.5px; }
  header .sub { color:var(--muted); font-size:12px; }
  main { display:grid; grid-template-columns: 300px 1fr 340px; gap:14px; padding:14px 22px; }
  @media (max-width:1100px){ main { grid-template-columns:1fr; } }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px; }
  .card h2 { font-size:13px; text-transform:uppercase; letter-spacing:1px; color:var(--muted); margin:0 0 10px; }
  #chat { height:420px; overflow-y:auto; display:flex; flex-direction:column; gap:8px; font-size:14px; }
  .msg { padding:8px 12px; border-radius:10px; max-width:85%; white-space:pre-wrap; word-break:break-word; }
  .msg.user { align-self:flex-end; background:#1d4ed8; }
  .msg.agent { align-self:flex-start; background:#1c2230; }
  .msg.tool { align-self:flex-start; background:#2a2413; border:1px solid #4a3f1a; }
  .msg .tag { font-size:10px; color:var(--accent); text-transform:uppercase; display:block; margin-bottom:4px; }
  #inputbar { display:flex; gap:8px; margin-top:10px; }
  input,select,button { background:#0d1117; color:var(--text); border:1px solid var(--border); border-radius:8px; padding:8px 12px; font-size:14px; }
  input { flex:1; } button { cursor:pointer; } button:hover { border-color:var(--accent); }
  .pill { display:inline-block; font-size:11px; padding:2px 8px; border-radius:99px; border:1px solid var(--border); margin:2px; color:var(--muted); }
  .pill.ok { color:var(--ok); border-color:#1f4a34; }
  .pill.review { color:var(--warn); border-color:#4a3f1a; }
  .pill.deny { color:var(--bad); border-color:#4a2020; }
  ul { list-style:none; padding:0; margin:0; font-size:13px; }
  li { padding:5px 0; border-bottom:1px solid var(--border); }
  li:last-child { border-bottom:none; }
  .small { font-size:11px; color:var(--muted); }
  .row { display:flex; justify-content:space-between; align-items:center; gap:8px; }
  .approve-btn { background:#1f4a34; color:var(--ok); }
  .status { font-size:12px; color:var(--ok); }
</style>
</head>
<body>
<header>
  <img src="/api/logo" alt="THE FOCUX">
  <div>
    <h1>THE FOCUX Agent</h1>
    <div class="sub">Agente de negocio: contenido · ecommerce · oportunidades · monetización</div>
  </div>
  <div style="margin-left:auto"><span id="status" class="status">cargando…</span></div>
</header>
<main>
  <div style="display:flex;flex-direction:column;gap:14px">
    <div class="card"><h2>Skills (<span id="skillCount">0</span>)</h2><ul id="skills"></ul></div>
    <div class="card"><h2>Memoria</h2>
      <div class="row"><span class="small">workspace</span><input id="workspace" value="default" style="max-width:120px"></div>
      <button onclick="loadMemory()" style="width:100%;margin-top:8px">recargar memoria</button>
      <ul id="memory" style="margin-top:8px"></ul>
    </div>
  </div>
  <div class="card">
    <h2>Chat con tu agente</h2>
    <div id="chat"></div>
    <div id="inputbar">
      <select id="pillar">
        <option value="content">contenido</option>
        <option value="commerce">ecommerce</option>
        <option value="monetization">monetización</option>
        <option value="research">research</option>
        <option value="account">cuenta</option>
      </select>
      <input id="message" placeholder="Pídele algo a THE FOCUX…" onkeydown="if(event.key==='Enter')send()">
      <button onclick="send()">Enviar</button>
    </div>
    <div class="card" style="margin-top:14px"><h2>Herramientas (gateadas)</h2>
      <div class="row" style="flex-wrap:wrap">
        <select id="tool"><option>publish_post</option><option>send_email</option><option>create_listing</option><option>make_payment</option><option>update_credentials</option><option>draft_content</option><option>ping</option></select>
        <input id="toolArgs" placeholder='{"platform":"linkedin"}' style="flex:1">
        <button onclick="runTool()">Ejecutar tool</button>
      </div>
      <div id="approvals" class="small" style="margin-top:8px"></div>
    </div>
  </div>
  <div style="display:flex;flex-direction:column;gap:14px">
    <div class="card"><h2>Drafts cristalizados</h2><button onclick="loadDrafts()" style="width:100%;margin-bottom:8px">recargar drafts</button><ul id="drafts"></ul></div>
    <div class="card"><h2>Estado</h2><ul id="state"></ul></div>
  </div>
</main>
<script>
const $=id=>document.getElementById(id);
function addMsg(role, text, tag){ const m=document.createElement('div'); m.className='msg '+role;
  if(tag){ const t=document.createElement('span'); t.className='tag'; t.textContent=tag; m.appendChild(t); }
  m.appendChild(document.createTextNode(text)); $('chat').appendChild(m); $('chat').scrollTop=$('chat').scrollHeight; }
async function api(path, body){ const r=await fetch(path, body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:undefined);
  return r.json(); }
async function refresh(){ const s=await api('/api/status'); $('status').textContent='operativo';
  $('skillCount').textContent=s.skills; loadSkills(s.names); }
async function loadSkills(names){ $('skills').innerHTML=''; (names||[]).slice(0,12).forEach(n=>{const li=document.createElement('li');li.textContent=n;$('skills').appendChild(li);}); }
async function send(){ const msg=$('message').value; if(!msg)return; addMsg('user',msg); $('message').value='';
  const r=await api('/api/chat',{message:msg,pillar:$('pillar').value,workspace:$('workspace').value});
  if(r.reply) addMsg('agent', r.reply, r.decision||'draft');
  if(r.approvals) r.approvals.forEach(a=>addMsg('tool','APROBACIÓN REQUERIDA: '+a.summary, a.decision)); }
async function runTool(){ const t=$('tool').value; let args={}; try{args=JSON.parse($('toolArgs').value||'{}');}catch(e){addMsg('agent','JSON inválido en args','error');return;}
  const r=await api('/api/tool',{tool:t,args}); addMsg('tool', JSON.stringify(r,null,2), r.decision);
  renderApprovals(r.approval_hint, r.idempotency_key); }
function renderApprovals(hint,key){ if(!hint)return; const d=document.createElement('div'); d.className='row';
  d.innerHTML='<span>'+hint+'</span><button class="approve-btn" onclick="approve(\''+key+'\')">Aprobar</button>';
  $('approvals').appendChild(d); }
async function approve(key){ const r=await api('/api/approve',{idempotency_key:key}); addMsg('tool', r.message, 'aprobación'); }
async function loadMemory(){ const w=$('workspace').value; const r=await api('/api/memory?workspace='+encodeURIComponent(w));
  $('memory').innerHTML='';
  (r.facts||[]).forEach(f=>{const li=document.createElement('li');li.innerHTML='<b>'+f.key+'</b>: '+f.value;$('memory').appendChild(li);});
  (r.events||[]).slice(0,5).forEach(e=>{const li=document.createElement('li');li.className='small';li.textContent=e.kind+' · '+e.created_at;$('memory').appendChild(li);}); }
async function loadDrafts(){ const r=await api('/api/drafts'); $('drafts').innerHTML='';
  (r.drafts||[]).forEach(d=>{const li=document.createElement('li');li.className='row';
    li.innerHTML='<span>'+d.name+' <span class="small">(DRAFT)</span></span><button class="approve-btn" onclick="promote(\''+d.name+'\')">Promover</button>';
    $('drafts').appendChild(li);}); }
async function promote(name){ const r=await api('/api/promote',{name}); addMsg('tool', r.message, 'promoción'); loadDrafts(); }
async function loadState(){ const r=await api('/api/status'); $('state').innerHTML='';
  const rows=[['skills',r.skills],['memoria',r.memory],['drafts',r.drafts],['gates','money-gate activo'],['constitución','3 leyes']];
  rows.forEach(([k,v])=>{const li=document.createElement('li');li.innerHTML='<b>'+k+'</b>: '+v;$('state').appendChild(li);}); }
refresh(); loadDrafts(); loadState();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence default logging
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            body = CONSOLE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == "/api/logo":
            mark = REPO / "assets" / "the-focux-mark-1024.png"
            if mark.is_file():
                body = mark.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json({"detail": "logo missing"}, 404)
        elif parsed.path == "/api/status":
            agent = get_agent()
            mem = agent.memory
            self._json({
                "skills": len(agent.skills),
                "names": [s.name for s in agent.skills],
                "memory": len(mem.facts(agent.workspace)) if mem else 0,
                "drafts": len(list_drafts(REPO / "skills-draft")),
                "workspace": agent.workspace,
                "gate": "money-gate activo",
            })
        elif parsed.path == "/api/skills":
            agent = get_agent()
            self._json({"skills": [s.as_dict() if hasattr(s, "as_dict") else {
                "name": s.name, "description": s.description
            } for s in agent.skills]})
        elif parsed.path.startswith("/api/memory"):
            agent = get_agent()
            qs = parse_qs(parsed.query)
            workspace = qs.get("workspace", [agent.workspace])[0]
            mem = agent.memory
            if mem is None:
                self._json({"facts": [], "events": [], "procedures": []})
                return
            self._json({
                "facts": [f.as_dict() for f in mem.facts(workspace)],
                "events": [e.as_dict() for e in mem.recent_events(workspace)],
                "procedures": [p.as_dict() for p in mem.procedures(workspace)],
            })
        elif parsed.path == "/api/drafts":
            drafts = list_drafts(REPO / "skills-draft")
            self._json({"drafts": [{"name": s.name, "description": s.description} for s in drafts]})
        else:
            self._json({"detail": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self._read_body()
        if parsed.path == "/api/chat":
            agent = get_agent()
            message = str(body.get("message", ""))
            pillar = str(body.get("pillar", "content"))
            workspace = str(body.get("workspace", agent.workspace))
            result = agent.propose(pillar=pillar, objective=message)
            reply = ""
            if result.decision == "ALLOW":
                try:
                    reply = agent.draft(message)
                except Exception as exc:  # noqa: BLE001
                    reply = f"(draft unavailable: {type(exc).__name__})"
            self._json({
                "decision": result.decision,
                "summary": result.summary,
                "reply": reply or result.summary,
            })
        elif parsed.path == "/api/tool":
            from runtime.tools import ToolRegistry

            agent = get_agent()
            reg = ToolRegistry(gate=default_gate())
            tool = str(body.get("tool", ""))
            args = body.get("args", {}) if isinstance(body.get("args", {}), dict) else {}
            tr = reg.request(tool, args)
            # SECURITY (round 10): the idempotency key must never embed
            # secrets from args — redact before building it.
            from runtime.redact import redact_mapping

            safe_args = redact_mapping(dict(args))
            key = f"tool:{tool}:{str(safe_args)[:80]}"
            if tr.decision == "REVIEW":
                _pending[key] = {"tool": tool, "args": args}
            self._json({
                "decision": tr.decision,
                "output": tr.output,
                "approval_hint": tr.approval_hint,
                "idempotency_key": key,
            })
        elif parsed.path == "/api/approve":
            key = str(body.get("idempotency_key", ""))
            if key in _pending:
                info = _pending.pop(key)
                self._json({"message": f"aprobado: {info['tool']} (en la vida real, ahora se ejecuta)"})
            else:
                self._json({"message": "no hay tarjeta pendiente con esa key"}, 404)
        elif parsed.path == "/api/promote":
            name = str(body.get("name", ""))
            try:
                target = promote_skill(REPO / "skills-draft", REPO / "skills", name)
                self._json({"message": f"promovido: {name} -> {target}"})
            except Exception as exc:  # noqa: BLE001
                self._json({"message": f"no se pudo promover: {exc}"}, 400)
        else:
            self._json({"detail": "not found"}, 404)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="focux-web", description="THE FOCUX web console")
    parser.add_argument("--port", type=int, default=3080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"THE FOCUX console: http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
