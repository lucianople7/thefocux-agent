"""Tests for the real-data ingestion brain (sensors + memory storage)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.ingest import (  # noqa: E402
    GitHubSensor,
    HFSensor,
    SensorResult,
    XSensor,
    absorb,
    format_absorb,
    store_results,
)
from runtime.memory import FocuxMemory  # noqa: E402


# --- sensors (mocked HTTP) ---------------------------------------------------

def test_github_sensor_parses(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "runtime.ingest._get_json",
        lambda url, headers=None, timeout=30: {
            "items": [
                {"full_name": "a/b", "stargazers_count": 5000,
                 "description": "great repo", "language": "Python",
                 "html_url": "https://github.com/a/b"},
            ]
        },
    )
    result = GitHubSensor(query="ai", limit=5).fetch()
    assert result.ok
    assert len(result.items) == 1
    item = result.items[0]
    assert item["repo"] == "a/b"
    assert item["stars"] == 5000
    assert item["language"] == "Python"


def test_github_sensor_handles_error(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def boom(url, headers=None, timeout=30):
        raise RuntimeError("network down")

    monkeypatch.setattr("runtime.ingest._get_json", boom)
    result = GitHubSensor().fetch()
    assert not result.ok
    assert "network down" in result.error


def test_hf_sensor_parses(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake(url, headers=None, timeout=30):
        if "/models" in url:
            return [{"id": "Qwen/Qwen3", "downloads": 100, "likes": 5,
                     "pipeline_tag": "text-generation"}]
        return [{"id": "datasets/x", "downloads": 50}]

    monkeypatch.setattr("runtime.ingest._get_json", fake)
    result = HFSensor(limit=5).fetch()
    assert result.ok
    assert len(result.items) == 2
    assert result.items[0]["type"] == "model"
    assert result.items[1]["type"] == "dataset"


def test_x_sensor_degrades_honestly_without_token() -> None:
    result = XSensor(bearer_token="").fetch()
    assert not result.ok
    assert "token" in result.error
    assert "no data invented" in result.error


def test_x_sensor_with_token_parses(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "runtime.ingest._get_json",
        lambda url, headers=None, timeout=30: {
            "data": [{"id": "1", "text": "AI agents are the future"}]
        },
    )
    result = XSensor(bearer_token="tok", query="AI").fetch()
    assert result.ok
    assert result.items[0]["text"].startswith("AI agents")


# --- absorb + store ----------------------------------------------------------

def test_absorb_runs_selected_sources(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake(url, headers=None, timeout=30):
        if "api.github.com" in url:
            return {"items": [{"full_name": "x/y", "stargazers_count": 1,
                               "description": "", "language": "",
                               "html_url": ""}]}
        if "huggingface.co" in url and "/models" in url:
            return [{"id": "m", "downloads": 1, "likes": 0, "pipeline_tag": ""}]
        return [{"id": "d", "downloads": 1}]

    monkeypatch.setattr("runtime.ingest._get_json", fake)
    results = absorb(sources=("github", "huggingface"), limit=3)
    assert set(results) == {"github", "huggingface"}
    assert results["github"].ok
    assert results["huggingface"].ok


def test_store_results_in_memory(tmp_path: Path) -> None:
    mem = FocuxMemory(tmp_path / "m.db")
    results = {
        "github": SensorResult(source="github", ok=True,
                               items=({"repo": "a", "stars": 1}, {"repo": "b", "stars": 2}),
                               fetched_at="now"),
        "x": SensorResult(source="x", ok=False, error="no token", fetched_at="now"),
    }
    stored = store_results(results, mem, workspace="biz")
    assert stored == 2  # only github items stored; x error stored separately
    events = mem.recent_events("biz")
    kinds = {e.kind for e in events}
    assert "absorb:github" in kinds
    assert "absorb:x:error" in kinds
    mem.close()


def test_format_absorb() -> None:
    results = {
        "github": SensorResult(
            source="github", ok=True,
            items=({"repo": "a/b", "stars": 42, "language": "Python",
                    "description": "desc"},),
            fetched_at="now",
        ),
        "x": SensorResult(source="x", ok=False, error="token required",
                          fetched_at="now"),
    }
    text = format_absorb(results)
    assert "=== github ===" in text
    assert "a/b" in text
    assert "=== x ===" in text
    assert "token required" in text


def test_sensor_result_serializable() -> None:
    r = SensorResult(source="github", ok=True, items=({"a": 1},), fetched_at="t")
    d = r.as_dict()
    assert d["source"] == "github"
    assert d["ok"] is True
    assert d["items"] == [{"a": 1}]


def test_sensors_sanitize_non_ascii(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Emoji/accents from real APIs must never crash cp1252 consoles."""
    monkeypatch.setattr(
        "runtime.ingest._get_json",
        lambda url, headers=None, timeout=30: {
            "items": [{"full_name": "emoji/repo", "stargazers_count": 1,
                       "description": "nuevo modelo \u2605\u2605 and \U0001f680 rocket",
                       "language": "Espa\u00f1ol", "html_url": "https://x.io/r"}]
        },
    )
    result = GitHubSensor().fetch()
    for item in result.items:
        for key, value in item.items():
            if isinstance(value, str):
                value.encode("ascii")  # must not raise
    text = format_absorb({"github": result})
    text.encode("ascii")  # must not raise
    assert "nuevo modelo ?? and ? rocket" in text


# --- LIVE API test (real network; skipped if offline) ------------------------

def test_live_github_api() -> None:
    """REAL GitHub search — verifies the sensor works against the live API."""
    result = GitHubSensor(query="ai agent", limit=3).fetch()
    if not result.ok:
        pytest.skip(f"network/API unavailable: {result.error}")
    assert len(result.items) >= 1
    assert result.items[0]["repo"]


def test_live_hf_api() -> None:
    """REAL Hugging Face trending models — verifies the sensor live."""
    result = HFSensor(limit=3).fetch()
    if not result.ok:
        pytest.skip(f"network/API unavailable: {result.error}")
    assert len(result.items) >= 1
