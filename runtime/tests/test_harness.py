"""Tests for THE FOCUX HARNESS: make any software agent-native."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

import runtime.harness as harness_mod  # noqa: E402
from runtime.harness import (  # noqa: E402
    _extract_python,
    generate_harness,
    list_harnesses,
    refine_harness,
    run_harness,
)
from runtime.agent import FocuxAgent  # noqa: E402
from policy.money_gate import ActionClass, MoneyGate, PolicyRule  # noqa: E402

COMMANDS_PY = """import math

def square(**kwargs):
    n = float(kwargs.get("n", 0))
    return {"n": n, "square": n * n}

def cube(**kwargs):
    n = float(kwargs.get("n", 0))
    return {"n": n, "cube": n ** 3}

COMMANDS = [
    {"group": "math", "name": "square", "help": "square a number",
     "args": [{"name": "n", "type": "float", "required": True}],
     "func": "square"},
    {"group": "math", "name": "cube", "help": "cube a number",
     "args": [{"name": "n", "type": "float", "required": True}],
     "func": "cube"},
]
"""


class _DesignLLM:
    """Stub: returns the commands.py fenced block for generate and refine."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages) -> str:  # type: ignore[no-untyped-def]
        self.calls += 1
        return "```python\n" + COMMANDS_PY + "\n```"


def _gate() -> MoneyGate:
    return MoneyGate({
        ActionClass.READ: PolicyRule(ActionClass.READ, max_amount=0.0,
                                     auto_approve=True),
    })


def _agent(llm=None) -> FocuxAgent:  # type: ignore[no-untyped-def]
    return FocuxAgent(llm=llm or _DesignLLM(), gate=_gate(), memory=None,
                      workspace="biz")  # type: ignore[arg-type]


@pytest.fixture()
def target(tmp_path: Path) -> Path:
    root = tmp_path / "target"
    root.mkdir(parents=True)
    (root / "mod.py").write_text(
        "def square(n):\n    return n * n\n", encoding="utf-8")
    return root


@pytest.fixture()
def harness_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "harnesses"
    monkeypatch.setattr(harness_mod, "HARNESS_DIR", d)
    return d


def test_extract_python_fenced() -> None:
    text = "intro\n```python\ndef x():\n    pass\n```\ntrailing"
    code = _extract_python(text)
    assert "def x():" in code
    assert "```" not in code
    assert _extract_python("no code") == ""


def test_generate_harness_verified(target: Path, harness_dir: Path) -> None:
    result = generate_harness(_agent(), target, name="demo")
    assert result.name == "demo"
    assert (harness_dir / "demo" / "cli.py").exists()
    assert (harness_dir / "demo" / "commands.py").exists()
    assert (harness_dir / "demo" / "SKILL.md").exists()
    assert (harness_dir / "demo" / "test_cli.py").exists()
    assert "verified" in result.note  # --help really ran


def test_harness_runs_command(target: Path, harness_dir: Path) -> None:
    generate_harness(_agent(), target, name="demo")
    proc = subprocess.run(
        [sys.executable, str(harness_dir / "demo" / "cli.py"),
         "--json", "math", "square", "--n", "4"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    import json

    data = json.loads(proc.stdout)
    assert data["square"] == 16


def test_run_harness_cli(target: Path, harness_dir: Path,
                         monkeypatch: pytest.MonkeyPatch) -> None:
    generate_harness(_agent(), target, name="demo")
    monkeypatch.setattr(harness_mod, "HARNESS_DIR", harness_dir)
    assert run_harness("demo", ["--help"]) == 0
    with pytest.raises(FileNotFoundError):
        run_harness("nope", [])


def test_harness_list(target: Path, harness_dir: Path) -> None:
    generate_harness(_agent(), target, name="demo")
    assert [h["name"] for h in list_harnesses()] == ["demo"]


def test_refine_extends(target: Path, harness_dir: Path) -> None:
    llm = _DesignLLM()
    generate_harness(_agent(llm), target, name="demo")
    result = refine_harness(_agent(llm), "demo", "add cube")
    assert "refined" in result.note
    text = (harness_dir / "demo" / "commands.py").read_text(encoding="utf-8")
    assert "def cube" in text
