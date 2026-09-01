"""Tests for the PROJECT MAP (deterministic local graph) + LESSONS."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from runtime.projectmap import (  # noqa: E402
    INFERRED,
    build_graph,
    explain,
    query,
    save_graph,
    shortest_path,
)
from runtime.lessons import lessons, reflect, save_lesson  # noqa: E402
from runtime.memory import FocuxMemory  # noqa: E402


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "core.py").write_text(
        "import os\n"
        "from pkg import helper\n"
        "\n"
        "class Engine:\n"
        "    def start(self):\n"
        "        return helper.run()\n"
        "\n"
        "def build():\n"
        "    return Engine()\n",
        encoding="utf-8",
    )
    (root / "pkg" / "helper.py").write_text(
        "def run():\n    return 'ok'\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# Project\n\n## Architecture\nSee [core](pkg/core.py)\n",
        encoding="utf-8")
    return root


def test_build_graph_deterministic(project: Path) -> None:
    g1 = build_graph(project)
    g2 = build_graph(project)
    assert g1.as_dict()["counts"] == g2.as_dict()["counts"]  # deterministic
    assert g1.as_dict()["counts"]["nodes"] >= 8  # files, classes, funcs, docs
    # EXTRACTED edges exist (contains, imports)
    tags = {e["tag"] for e in g1.edges}
    assert tags == {INFERRED, "EXTRACTED"}
    # both classes/functions present
    ids = set(g1.nodes)
    assert any(i.startswith("class:pkg/core.py::Engine") for i in ids)
    assert any(i.startswith("function:pkg/helper.py::run") for i in ids)
    # docs mapped
    assert any(i.startswith("doc:README.md") for i in ids)


def test_explain_engine(project: Path) -> None:
    g = build_graph(project)
    result = explain(g, "Engine")
    assert result["found"]
    assert result["node"]["kind"] == "class"
    assert result["degree"] >= 2  # contains + INFERRED calls


def test_shortest_path(project: Path) -> None:
    g = build_graph(project)
    result = shortest_path(g, "Engine", "run")
    assert result["found"]
    assert result["hops"] >= 1
    # the path actually connects the two
    assert result["path"][0].endswith("Engine")
    assert result["path"][-1].endswith("run")


def test_query_keyword_scored(project: Path) -> None:
    g = build_graph(project)
    result = query(g, "engine start")
    assert result["matched"] >= 1
    names = {n["name"] for n in result["nodes"]}
    assert "Engine" in names


def test_save_and_load_graph(project: Path, tmp_path: Path) -> None:
    g = build_graph(project)
    path = save_graph(g, tmp_path / "out")
    from runtime.projectmap import load_graph

    loaded = load_graph(path)
    assert loaded.as_dict()["counts"] == g.as_dict()["counts"]


# --- lessons ----------------------------------------------------------------

def test_lessons_roundtrip(tmp_path: Path) -> None:
    mem = FocuxMemory(tmp_path / "m.db")
    save_lesson(mem, "biz", "Los datos reales ganan a las opiniones")
    save_lesson(mem, "biz", "Nunca publicar sin hook")
    items = lessons(mem, "biz")
    assert len(items) == 2
    target = reflect(mem, "biz", out=tmp_path / "lessons.md")
    text = target.read_text(encoding="utf-8")
    assert "Los datos reales ganan" in text
    assert "Nunca publicar sin hook" in text
    mem.close()


def test_reflect_empty(tmp_path: Path) -> None:
    mem = FocuxMemory(tmp_path / "m.db")
    target = reflect(mem, "biz", out=tmp_path / "lessons.md")
    assert "no lessons yet" in target.read_text(encoding="utf-8")
    mem.close()
