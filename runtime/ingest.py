"""FOCUX ingestion — the brain absorbs REAL data from the world.

Sensors pull live signals that feed ANALIZAR/PLANIFICAR:

- **GitHubSensor** — what is growing: search repos by topic, sorted by stars
  (public API, no auth, rate-limited ~10/min unauthenticated).
- **HFSensor** — what is coming: trending models and datasets on Hugging Face
  (public API).
- **XSensor** — what works in the niche: requires an optional bearer token
  (X API v2). Without a token it degrades HONESTLY — reports "token required"
  instead of inventing data.

Every sensor returns structured, redacted data; the CLI stores it as memory
events so the brain can ANALIZAR with real signals, not vibes. No sensor ever
executes an action — ingestion is read-only.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .redact import redact_mapping


@dataclass(frozen=True)
class SensorResult:
    source: str
    ok: bool
    items: tuple[dict[str, object], ...] = ()
    error: str = ""
    fetched_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "ok": self.ok,
            "items": list(self.items),
            "error": self.error,
            "fetched_at": self.fetched_at,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _ascii(value: str, max_len: int = 0) -> str:
    """Force ASCII — Windows cp1252 consoles crash on emoji/accents.

    Non-ASCII characters become '?'; this keeps stored data and CLI output
    safe on any console without lying about the data.
    """
    out = value.encode("ascii", errors="replace").decode("ascii")
    return out[:max_len] if max_len else out


def _get_json(url: str, headers: dict[str, str] | None = None,
              timeout: int = 30) -> Any:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


class GitHubSensor:
    """Repos growing in a topic (public search API)."""

    def __init__(self, *, query: str = "ai agent", limit: int = 10) -> None:
        self.query = query
        self.limit = limit

    def fetch(self) -> SensorResult:
        try:
            url = (
                "https://api.github.com/search/repositories"
                f"?q={urllib.parse.quote(self.query)}"
                f"&sort=stars&order=desc&per_page={self.limit}"
            )
            data = _get_json(url, headers={"User-Agent": "focux-brain"})
            items = tuple(
                redact_mapping({
                    "repo": _ascii(str(item.get("full_name", "")), 120),
                    "stars": int(item.get("stargazers_count", 0) or 0),
                    "description": _ascii(str(item.get("description", "") or ""), 140),
                    "language": _ascii(str(item.get("language", "") or ""), 40),
                    "url": _ascii(str(item.get("html_url", "")), 200),
                })
                for item in data.get("items", [])
            )
            return SensorResult(source="github", ok=True, items=items,
                                fetched_at=_now())
        except Exception as exc:  # noqa: BLE001
            return SensorResult(
                source="github", ok=False, error=f"{type(exc).__name__}: {exc}",
                fetched_at=_now(),
            )


class HFSensor:
    """Trending models + datasets on Hugging Face."""

    def __init__(self, *, limit: int = 10) -> None:
        self.limit = limit

    def fetch(self) -> SensorResult:
        try:
            models = _get_json(
                "https://huggingface.co/api/models"
                f"?sort=trendingScore&direction=-1&limit={self.limit}"
            )
            datasets = _get_json(
                "https://huggingface.co/api/datasets"
                f"?sort=trendingScore&direction=-1&limit={min(5, self.limit)}"
            )
            items = tuple(
                redact_mapping({
                    "type": "model",
                    "id": _ascii(str(m.get("id", "")), 160),
                    "downloads": int(m.get("downloads", 0) or 0),
                    "likes": int(m.get("likes", 0) or 0),
                    "pipeline": _ascii(str(m.get("pipeline_tag", "") or ""), 40),
                })
                for m in models[: self.limit]
            ) + tuple(
                redact_mapping({
                    "type": "dataset",
                    "id": _ascii(str(d.get("id", "")), 160),
                    "downloads": int(d.get("downloads", 0) or 0),
                })
                for d in datasets
            )
            return SensorResult(source="huggingface", ok=True, items=items,
                                fetched_at=_now())
        except Exception as exc:  # noqa: BLE001
            return SensorResult(
                source="huggingface", ok=False,
                error=f"{type(exc).__name__}: {exc}", fetched_at=_now(),
            )


class XSensor:
    """What works in the niche (X API v2; needs an optional bearer token).

    Without a token the sensor degrades HONESTLY: it reports that a token is
    required rather than fabricating data.
    """

    def __init__(self, *, bearer_token: str = "", query: str = "",
                 limit: int = 10) -> None:
        self.bearer = bearer_token
        self.query = query
        self.limit = limit

    def fetch(self) -> SensorResult:
        if not self.bearer:
            return SensorResult(
                source="x", ok=False,
                error="X API requires a bearer token (X_BEARER_TOKEN); "
                      "sensor disabled — no data invented",
                fetched_at=_now(),
            )
        try:
            url = (
                "https://api.x.com/2/tweets/search/recent"
                f"?query={urllib.parse.quote(self.query or 'AI agents')}"
                f"&max_results={self.limit}"
            )
            data = _get_json(url, headers={"Authorization": f"Bearer {self.bearer}"})
            items = tuple(
                redact_mapping({
                    "id": _ascii(str(t.get("id", "")), 40),
                    "text": _ascii(str(t.get("text", "")), 180),
                })
                for t in data.get("data", [])
            )
            return SensorResult(source="x", ok=True, items=items, fetched_at=_now())
        except urllib.error.HTTPError as exc:
            return SensorResult(
                source="x", ok=False,
                error=f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:120]}",
                fetched_at=_now(),
            )
        except Exception as exc:  # noqa: BLE001
            return SensorResult(
                source="x", ok=False, error=f"{type(exc).__name__}: {exc}",
                fetched_at=_now(),
            )


def absorb(
    *,
    sources: tuple[str, ...] = ("github", "huggingface"),
    github_query: str = "ai agent",
    x_bearer: str = "",
    x_query: str = "",
    limit: int = 10,
) -> dict[str, SensorResult]:
    """Run the selected sensors; returns {source: SensorResult}."""
    results: dict[str, SensorResult] = {}
    for source in sources:
        if source == "github":
            results["github"] = GitHubSensor(query=github_query, limit=limit).fetch()
        elif source == "huggingface":
            results["huggingface"] = HFSensor(limit=limit).fetch()
        elif source == "x":
            results["x"] = XSensor(bearer_token=x_bearer, query=x_query,
                                   limit=limit).fetch()
    return results


def store_results(
    results: dict[str, SensorResult],
    memory,
    workspace: str = "default",
) -> int:
    """Store sensor results as memory events; returns items stored."""
    stored = 0
    for source, result in results.items():
        if not result.ok:
            memory.remember_event(workspace, f"absorb:{source}:error",
                                  {"error": result.error, "at": result.fetched_at})
            continue
        memory.remember_event(workspace, f"absorb:{source}", {
            "fetched_at": result.fetched_at,
            "items": [i for i in result.items],
        })
        stored += len(result.items)
    return stored


def format_absorb(results: dict[str, SensorResult]) -> str:
    lines: list[str] = []
    for source, result in results.items():
        lines.append(f"=== {source} ===")
        if not result.ok:
            lines.append(f"  X {result.error}")
            continue
        for item in result.items:
            if source == "github":
                lines.append(_ascii(
                    f"  *{item.get('stars', 0):>7} {item.get('repo', '')} "
                    f"[{item.get('language', '')}] - {item.get('description', '')[:80]}",
                    160,
                ))
            elif source == "huggingface":
                lines.append(_ascii(
                    f"  {item.get('type', ''):8s} {item.get('id', '')} "
                    f"(downloaded {item.get('downloads', 0)})",
                    160,
                ))
            elif source == "x":
                lines.append(_ascii(f"  {item.get('text', '')[:100]}", 120))
    return "\n".join(lines)


def recent_signals(
    memory,
    workspace: str = "default",
    *,
    per_source: int = 3,
    max_events: int = 100,
) -> list[str]:
    """Latest absorbed REAL data as compact fact lines for ANALIZAR.

    Reads the newest ``absorb:<source>`` memory events (errors excluded) and
    formats them deterministically — no retrieval keyword needed, no JSON
    truncation. This is the concrete path that makes absorbed data a FACT
    the brain reasons with.
    """
    lines: list[str] = []
    counts: dict[str, int] = {}
    for event in memory.recent_events(workspace, limit=max_events):
        kind: str = event.kind
        if not kind.startswith("absorb:") or kind.endswith(":error"):
            continue
        source = kind.split(":", 1)[1]
        if counts.get(source, 0) >= per_source:
            continue
        for item in event.data.get("items", []):
            if counts.get(source, 0) >= per_source:
                break
            if source == "github":
                lines.append(_ascii(
                    f"github: {item.get('repo', '')} "
                    f"({item.get('stars', 0)} stars, {item.get('language', '')}) "
                    f"- {item.get('description', '')[:70]}",
                    180,
                ))
            elif source == "huggingface":
                lines.append(_ascii(
                    f"huggingface: {item.get('type', '')} {item.get('id', '')} "
                    f"({item.get('downloads', 0)} downloads)",
                    180,
                ))
            elif source == "x":
                lines.append(_ascii(f"x: {item.get('text', '')[:100]}", 140))
            counts[source] = counts.get(source, 0) + 1
    return lines


def signals_block(memory, workspace: str = "default") -> str:
    """Markdown block with absorbed signals; empty when nothing absorbed."""
    signals = recent_signals(memory, workspace)
    if not signals:
        return ""
    return "## Absorbed signals (REAL data)\n" + "\n".join(
        f"- {s}" for s in signals
    )
