"""THE FOCUX PROJECT MAP — see the project itself as a queryable graph.

Pattern absorbed from Graphify (Apache-2.0/MIT): instead of grepping files,
map the project into a knowledge graph you traverse. The FOCUX version is
STDLIB-ONLY and fully local:

- **Deterministic**: Python code is parsed with the `ast` module — no LLM,
  nothing leaves the machine. Docs (.md) become nodes too.
- **Every edge is explained**: each connection is tagged EXTRACTED (explicit
  in the source: import, call, inheritance, contains) or INFERRED (resolved
  by the map: import name -> module node, call target by name).
- **Not a vector index**: a real graph. `explain` shows a node and its
  neighbors; `shortest_path` traces hop by hop; `query` returns a
  keyword-scored subgraph (deterministic, honest).
"""

from __future__ import annotations
from .console import safe as _safe

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXTRACTED = "EXTRACTED"
INFERRED = "INFERRED"

#: dirs never mapped (build/runtime/cache)
_SKIP_DIRS = {".focux", ".git", ".venv", "venv", "__pycache__",
              "node_modules", ".pytest_cache", "graphify-out", "memory"}


@dataclass
class Graph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, str]] = field(default_factory=list)

    def add_node(self, node_id: str, kind: str, name: str, source: str = "",
                 line: int = 0, community: str = "") -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id, "kind": kind, "name": name, "source": source,
                "line": line, "community": community,
            }

    def add_edge(self, src: str, dst: str, edge_type: str,
                 tag: str = EXTRACTED) -> None:
        if src in self.nodes and dst in self.nodes:
            self.edges.append({"src": src, "dst": dst, "type": edge_type,
                               "tag": tag})

    def as_dict(self) -> dict[str, Any]:
        return {"nodes": list(self.nodes.values()),
                "edges": self.edges,
                "counts": {"nodes": len(self.nodes), "edges": len(self.edges)}}


def build_graph(root: Path, *, max_nodes: int = 800) -> Graph:
    """Deterministic project map: Python AST + markdown docs (stdlib only)."""
    graph = Graph()
    root = root.resolve()
    pending_calls: list[tuple[str, str]] = []  # (caller_id, callee_name)

    # --- python files: AST pass ---------------------------------------------
    for path in sorted(root.rglob("*.py")):
        if _skipped(path, root):
            continue
        rel = path.relative_to(root).as_posix()
        node_id = f"file:{rel}"
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        if len(graph.nodes) >= max_nodes:
            break
        graph.add_node(node_id, "file", rel, source=rel)
        for child in ast.walk(tree):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(graph.nodes) >= max_nodes:
                    break
                kind = "class" if isinstance(child, ast.ClassDef) else "function"
                cid = f"{kind}:{rel}::{child.name}"
                graph.add_node(cid, kind, child.name, source=rel,
                               line=getattr(child, "lineno", 0))
                # contains: module -> member (EXTRACTED)
                graph.add_edge(node_id, cid, "contains", EXTRACTED)
                # record call sites for cross-file resolution (INFERRED)
                for sub in ast.walk(child):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                        pending_calls.append((cid, sub.func.id))
                    elif isinstance(sub, ast.Call) and isinstance(
                            sub.func, ast.Attribute):
                        pending_calls.append((cid, sub.func.attr))
                # inheritance (EXTRACTED, same file; cross-file resolved below)
                if isinstance(child, ast.ClassDef):
                    for base in child.bases:
                        if isinstance(base, ast.Name):
                            parent = f"class:{rel}::{base.id}"
                            if parent in graph.nodes:
                                graph.add_edge(cid, parent, "inherits", EXTRACTED)
        # imports (EXTRACTED edges to module nodes; resolution is INFERRED)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("__"):
                        continue  # dunder/stdlib-magic hubs are noise
                    module_id = f"module:{alias.name}"
                    graph.add_node(module_id, "module", alias.name,
                                   source="imports")
                    graph.add_edge(node_id, module_id, "imports", EXTRACTED)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("__"):
                    continue
                module_id = f"module:{node.module}"
                graph.add_node(module_id, "module", node.module, source="imports")
                graph.add_edge(node_id, module_id, "imports", EXTRACTED)

    # --- cross-file resolution (INFERRED): calls by name across the graph ---
    name_index: dict[str, list[str]] = {}
    for nid, node in graph.nodes.items():
        if node["kind"] in ("class", "function"):
            name_index.setdefault(node["name"], []).append(nid)
    for caller_id, callee_name in pending_calls:
        for target in name_index.get(callee_name, []):
            if target != caller_id:
                graph.add_edge(caller_id, target, "calls", INFERRED)
                break  # first resolution wins; keeps the graph lean

    # --- markdown docs: headings + links ------------------------------------
    for path in sorted(root.rglob("*.md")):
        if _skipped(path, root):
            continue
        rel = path.relative_to(root).as_posix()
        doc_id = f"doc:{rel}"
        graph.add_node(doc_id, "doc", rel, source=rel)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines):
            m = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
            if m:
                heading_id = f"{doc_id}::{m.group(2).strip()}"
                graph.add_node(heading_id, "heading", m.group(2).strip(),
                               source=rel, line=i + 1)
                graph.add_edge(doc_id, heading_id, "contains", EXTRACTED)
            for link in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", line):
                target = (path.parent / link).resolve()
                try:
                    target_rel = target.relative_to(root).as_posix()
                    graph.add_edge(doc_id, f"doc:{target_rel}", "links", INFERRED)
                except ValueError:
                    pass
    return graph


def _skipped(path: Path, root: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.relative_to(root).parts)


# ---------------------------------------------------------------------------
# Traversal (deterministic, real graph)
# ---------------------------------------------------------------------------

def explain(graph: Graph, name: str) -> dict[str, Any]:
    """A node and its neighbors with edge tags (EXTRACTED vs INFERRED)."""
    node = find_node(graph, name)
    if node is None:
        return {"found": False, "name": name}
    neighbors = []
    for edge in graph.edges:
        if edge["src"] == node["id"]:
            other = graph.nodes.get(edge["dst"])
            if other:
                neighbors.append({"node": other["id"], "kind": other["kind"],
                                  "type": edge["type"], "tag": edge["tag"],
                                  "direction": "out"})
        elif edge["dst"] == node["id"]:
            other = graph.nodes.get(edge["src"])
            if other:
                neighbors.append({"node": other["id"], "kind": other["kind"],
                                  "type": edge["type"], "tag": edge["tag"],
                                  "direction": "in"})
    return {"found": True, "node": node,
            "degree": len(neighbors), "neighbors": neighbors}


def find_node(graph: Graph, name: str) -> dict[str, Any] | None:
    """Match by exact id, then by name (kind:name or last path segment)."""
    if name in graph.nodes:
        return graph.nodes[name]
    for node in graph.nodes.values():
        if node["name"] == name:
            return node
    tail = name.split("::")[-1]
    for node in graph.nodes.values():
        if node["name"].endswith(tail) and node["kind"] in ("class", "function"):
            return node
    return None


def shortest_path(graph: Graph, a: str, b: str) -> dict[str, Any]:
    """BFS hop-by-hop path between two concepts (undirected, real traversal)."""
    na, nb = find_node(graph, a), find_node(graph, b)
    if na is None or nb is None:
        return {"found": False, "from": a, "to": b,
                "reason": "one or both nodes not found"}
    if na["id"] == nb["id"]:
        return {"found": True, "hops": 0, "path": [na["id"]]}
    adj: dict[str, list[tuple[str, dict[str, str]]]] = {}
    for edge in graph.edges:
        adj.setdefault(edge["src"], []).append((edge["dst"], edge))
        adj.setdefault(edge["dst"], []).append((edge["src"], edge))
    from collections import deque

    queue = deque([na["id"]])
    prev: dict[str, tuple[str, dict[str, str]]] = {na["id"]: (None, {})}
    while queue:
        cur = queue.popleft()
        if cur == nb["id"]:
            break
        for nxt, edge in adj.get(cur, []):
            if nxt not in prev:
                prev[nxt] = (cur, edge)
                queue.append(nxt)
    if nb["id"] not in prev:
        return {"found": False, "from": a, "to": b, "reason": "no path"}
    path_ids: list[str] = []
    steps: list[dict[str, str]] = []
    cur = nb["id"]
    while cur is not None:
        path_ids.append(cur)
        back, edge = prev[cur]
        if back is not None:
            steps.append({"from": back, "to": cur, "type": edge.get("type", ""),
                          "tag": edge.get("tag", "")})
        cur = back
    path_ids.reverse()
    steps.reverse()
    return {"found": True, "hops": len(steps),
            "path": path_ids, "steps": steps}


def query(graph: Graph, question: str, *, limit: int = 8) -> dict[str, Any]:
    """Keyword-scored subgraph for a plain-language question (deterministic)."""
    tokens = {t for t in re.findall(r"[a-z0-9_]{3,}", question.lower())}
    scored: list[tuple[float, dict[str, Any]]] = []
    for node in graph.nodes.values():
        hay = f"{node['name']} {node['source']} {node['kind']}".lower()
        score = sum(1 for t in tokens if t in hay)
        if score:
            scored.append((score, node))
    scored.sort(key=lambda x: -x[0])
    top = [n for _, n in scored[:limit]]
    selected = {n["id"] for n in top}
    edges = [e for e in graph.edges if e["src"] in selected and e["dst"] in selected]
    return {"nodes": top, "edges": edges, "matched": len(top)}


# ---------------------------------------------------------------------------
# Persistence + formatting
# ---------------------------------------------------------------------------

def save_graph(graph: Graph, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "projectmap.json"
    path.write_text(json.dumps(graph.as_dict(), indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


def load_graph(path: Path) -> Graph:
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = Graph()
    for n in data.get("nodes", []):
        graph.nodes[n["id"]] = n
    graph.edges = list(data.get("edges", []))
    return graph


def format_map_summary(graph: Graph, root: Path) -> str:
    counts = graph.as_dict()["counts"]
    lines = [
        f"PROJECT MAP: {root}",
        f"  nodes: {counts['nodes']} | edges: {counts['edges']} "
        f"(local, deterministic, stdlib-only)",
    ]
    return _safe("\n".join(lines))


def format_explain(result: dict[str, Any]) -> str:
    if not result["found"]:
        return _safe(f"not found: {result['name']}")
    node = result["node"]
    lines = [f"Node: {node['name']}",
             f"  kind: {node['kind']} | source: {node['source']}"
             + (f":{node['line']}" if node.get("line") else "")
             + f" | degree: {result['degree']}"]
    for n in result["neighbors"][:25]:
        arrow = "-->" if n["direction"] == "out" else "<--"
        lines.append(f"  {arrow} {n['node']} [{n['type']}] [{n['tag']}]")
    return _safe("\n".join(lines))


def format_path(result: dict[str, Any]) -> str:
    if not result["found"]:
        return _safe(f"no path: {result.get('reason', '')}")
    lines = [f"Shortest path ({result['hops']} hops):"]
    if result["hops"] == 0:
        lines.append(f"  {result['path'][0]}")
    for step in result["steps"]:
        lines.append(f"  {step['from']} --{step['type']}--> {step['to']} "
                     f"[{step['tag']}]")
    return _safe("\n".join(lines))


def format_query(result: dict[str, Any]) -> str:
    lines = [f"Matched {result['matched']} nodes:"]
    for node in result["nodes"]:
        lines.append(f"  [{node['kind']}] {node['id']}"
                     + (f" :{node['line']}" if node.get("line") else ""))
    for edge in result["edges"][:12]:
        lines.append(f"    {edge['src']} --{edge['type']}--> {edge['dst']} [{edge['tag']}]")
    return _safe("\n".join(lines))


