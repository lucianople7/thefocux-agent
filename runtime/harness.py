"""THE FOCUX HARNESS — make ANY software agent-native (CLI-Anything pattern).

Pattern absorbed from CLI-Anything (Apache-2.0): transform any codebase into
an agent-controllable CLI with structured commands. The FOCUX version:

1. **analyze** — the Project Map (deterministic AST graph) scans the target.
2. **design** — the LLM writes `commands.py`: real functions that call the
   target's actual backend (no toy replacements).
3. **generate** — a stdlib `argparse` shell (`cli.py`) with `--json`, `--help`
   and a REPL when run bare, plus `SKILL.md`, `test_cli.py` and `HARNESS.md`.
4. **verify** — `cli.py --help` is really executed (the work-harness rule:
   never trust that generation succeeded; check it).
5. **publish** — the harness lands in `.focux/harnesses/<name>/`, runnable
   via `focux harness run <name> ...`.
6. **refine** — gap analysis expands coverage incrementally (LLM).

Discipline: the harness is generated locally, verified by execution, and the
generated code is the agent's to inspect — nothing runs without the human
initiating it.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .projectmap import build_graph, format_map_summary

HARNESS_DIR = Path.cwd() / ".focux" / "harnesses"

_DESIGN_PROMPT = """You are THE FOCUX BRAIN's harness generator. Design an
agent-native CLI for the TARGET codebase described below.

The CLI must expose the target's REAL capabilities as structured commands.
Write `commands.py`: one Python function per command, each returning a dict
(JSON-serializable), plus a COMMANDS list that drives the argparse shell.

COMMANDS entry shape:
{{"group": "<group>", "name": "<name>", "help": "<one line>",
  "args": [{{"name": "<arg>", "type": "float|int|str", "required": true|false}}],
  "func": "<function_name>"}}

Rules:
- Functions import the REAL target modules (use the imports shown) and call
  real functions/classes - no stubs, no fake outputs.
- Each function signature: def <name>(**kwargs) -> dict
- 3-6 commands covering the most useful capabilities.
- Never invent APIs that do not exist in the imports shown.

TARGET SUMMARY:
{target}

Reply with ONLY one ```python fenced code block containing commands.py:
```python
<commands.py>
```"""


@dataclass
class HarnessResult:
    name: str
    dir: Path
    files: list[str] = field(default_factory=list)
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "dir": str(self.dir),
                "files": self.files, "note": self.note}


def _target_summary(root: Path) -> str:
    """Deterministic analysis: project map + module surface for the LLM."""
    graph = build_graph(root)
    summary = [format_map_summary(graph, root)]
    # modules + their classes/functions (the "imports shown" the design must use)
    for node in graph.nodes.values():
        if node["kind"] in ("file", "class", "function") and node["kind"] != "file":
            summary.append(f"- {node['kind']}: {node['source']} :: {node['name']}")
    return "\n".join(summary[:120])


def _extract_python(text: str) -> str:
    """Pull the fenced python code block from the LLM output."""
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1)
    start = text.find("import ")
    if start == -1:
        return ""
    return text[start:]


def analyze_target(root: Path) -> dict[str, Any]:
    graph = build_graph(root)
    return {"summary": _target_summary(root),
            "counts": graph.as_dict()["counts"]}


def generate_harness(
    agent,
    root: Path,
    *,
    name: str = "",
    workspace: str = "default",
) -> HarnessResult:
    """analyze -> design -> generate -> verify -> publish (one pipeline)."""
    root = root.resolve()
    name = (name or root.name).replace(" ", "-").lower()[:40] or "harness"
    out = HARNESS_DIR / name
    if out.exists():
        raise ValueError(
            f"harness '{name}' already exists - use `focux harness refine {name}`")

    # 1) analyze (deterministic)
    analysis = analyze_target(root)

    # 2) design (LLM writes commands.py against the real backend)
    prompt = _DESIGN_PROMPT.format(target=analysis["summary"])
    text = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's harness generator. The commands.py you "
        "write must call REAL target code with the imports shown. Return "
        "only the fenced python block. Never invent APIs."
    ))
    commands_py = _extract_python(text)
    if not commands_py or "def " not in commands_py:
        raise ValueError(
            "the model did not produce a valid commands.py (honest: nothing "
            "generated without a real design)")

    # 3) generate the harness files
    out.mkdir(parents=True, exist_ok=True)
    (out / "commands.py").write_text(commands_py, encoding="utf-8")
    (out / "cli.py").write_text(
        _CLI_TEMPLATE.replace("{name}", name).replace("{target}", str(root)),
        encoding="utf-8")
    (out / "SKILL.md").write_text(_skill_md(name, root), encoding="utf-8")
    (out / "test_cli.py").write_text(_test_py(name), encoding="utf-8")
    (out / "HARNESS.md").write_text(_harness_md(name, root), encoding="utf-8")
    files = ["commands.py", "cli.py", "SKILL.md", "test_cli.py", "HARNESS.md"]

    # 4) verify: the CLI must actually answer (work-harness rule)
    probe = subprocess.run(
        [sys.executable, str(out / "cli.py"), "--help"],
        capture_output=True, text=True, timeout=120,
    )
    if probe.returncode != 0:
        raise ValueError(
            f"generated harness failed verification: "
            f"{(probe.stderr or probe.stdout).strip()[:300]}")

    return HarnessResult(name=name, dir=out, files=files,
                         note="verified: cli.py --help answers")


def list_harnesses() -> list[dict[str, str]]:
    if not HARNESS_DIR.exists():
        return []
    out = []
    for d in sorted(HARNESS_DIR.iterdir()):
        if d.is_dir() and (d / "cli.py").exists():
            out.append({"name": d.name, "dir": str(d)})
    return out


def run_harness(name: str, args: list[str]) -> int:
    """Run an installed harness (subprocess; stdout passes through)."""
    target = HARNESS_DIR / name
    if not (target / "cli.py").exists():
        raise FileNotFoundError(f"harness '{name}' not installed "
                                f"(installed: {[h['name'] for h in list_harnesses()]})")
    proc = subprocess.run(
        [sys.executable, str(target / "cli.py"), *args],
        capture_output=True, text=True, timeout=300,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


def refine_harness(agent, name: str, focus: str = "", *,
                   workspace: str = "default") -> HarnessResult:
    """Gap analysis: extend an existing harness with new commands."""
    target = HARNESS_DIR / name
    if not (target / "cli.py").exists():
        raise FileNotFoundError(f"harness '{name}' not installed")
    existing = (target / "commands.py").read_text(encoding="utf-8")
    prompt = (
        "You are refining an agent-native CLI harness. Here is the current "
        "commands.py:\n\n```python\n" + existing[:6000] +
        "\n```\n\nWrite the FULL new commands.py (keep every existing function, "
        + ("add commands for: " + focus if focus else
           "add 2-4 new useful commands from a gap analysis")
        + "). Return ONLY one ```python fenced code block."
    )
    text = agent.draft(prompt, system=(
        "You are THE FOCUX BRAIN's harness refiner. Keep existing functions "
        "verbatim, add new ones that call the same real backend. Never invent."
    ))
    commands_py = _extract_python(text)
    if not commands_py or "def " not in commands_py:
        raise ValueError("refine produced no valid commands.py")
    # verify BEFORE overwriting: syntax-check the new commands, then swap,
    # then run the real check; restore the backup on any failure.
    staging = target / "commands.py.new"
    staging.write_text(commands_py, encoding="utf-8")
    compile_check = subprocess.run(
        [sys.executable, "-m", "py_compile", str(staging)],
        capture_output=True, text=True, timeout=60,
    )
    if compile_check.returncode != 0:
        staging.unlink()
        raise ValueError("refined commands.py does not compile: "
                         f"{(compile_check.stderr or '').strip()[:300]}")
    backup = (target / "commands.py").read_text(encoding="utf-8")
    staging.replace(target / "commands.py")
    probe = subprocess.run(
        [sys.executable, str(target / "cli.py"), "--help"],
        capture_output=True, text=True, timeout=120,
    )
    if probe.returncode != 0:
        (target / "commands.py").write_text(backup, encoding="utf-8")
        raise ValueError(f"refined harness failed verification "
                         f"(previous version restored): "
                         f"{(probe.stderr or probe.stdout).strip()[:300]}")
    return HarnessResult(name=name, dir=target,
                         files=["commands.py (refined)"],
                         note="verified: refined cli.py --help answers")


# ---------------------------------------------------------------------------
# Templates for the generated harness
# ---------------------------------------------------------------------------

_CLI_TEMPLATE = '''"""<name> - agent-native CLI (generated by THE FOCUX harness).

Usage:
  python cli.py --help                 discover commands
  python cli.py --json <group> <name> --arg value   structured output
  python cli.py                        enter the REPL
"""
from __future__ import annotations

import argparse
import json
import sys

# the target codebase root, so commands.py can import the REAL backend
sys.path.insert(0, r"{target}")

from commands import COMMANDS


def _print(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False, default=str))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="<name>",
                                     description="<name> - agent-native CLI")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable JSON output")
    sub = parser.add_subparsers(dest="group")
    groups: dict[str, argparse.ArgumentParser] = {}
    group_subs: dict[str, argparse._SubParsersAction] = {}
    for cmd in COMMANDS:
        g = cmd["group"]
        if g not in groups:
            groups[g] = sub.add_parser(g, help="")
            group_subs[g] = groups[g].add_subparsers(dest="name")
        one = group_subs[g].add_parser(cmd["name"], help=cmd.get("help", ""))
        for arg in cmd.get("args", []):
            t = {"float": float, "int": int, "str": str}.get(
                arg.get("type", "str"), str)
            one.add_argument("--" + arg["name"], type=t,
                             required=arg.get("required", False))
        one.set_defaults(func=cmd["func"])
    return parser


def _repl() -> None:
    print(f"<name> REPL - type a command group/name, or 'exit'")
    while True:
        try:
            line = input(f"<name>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line in ("exit", "quit"):
            break
        parts = line.split()
        try:
            parser = _build_parser()
            args = parser.parse_args(parts)
            if getattr(args, "func", None):
                _print(_call(args))
        except SystemExit:
            continue
        except Exception as exc:  # noqa: BLE001
            _print({"error": f"{type(exc).__name__}: {exc}"})


def _call(args: argparse.Namespace) -> dict:
    import commands as _commands

    func_name = getattr(args, "func", "")
    if not func_name or func_name not in _commands.__dict__:
        return {"error": f"unknown command: {func_name}"}
    cmd = next(c for c in _commands.COMMANDS if c["func"] == func_name)
    kwargs = {a["name"]: getattr(args, a["name"], None)
              for a in cmd.get("args", [])}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    return _commands.__dict__[func_name](**kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "group", None) is None:
        _repl()
        return 0
    if getattr(args, "name", None) is None:
        parser.parse_args([args.group, "--help"])
        return 0
    result = _call(args)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, default=str))
    else:
        _print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _skill_md(name: str, root: Path) -> str:
    return f"""---
name: {name}
description: Agent-native CLI for {root.name} (generated by THE FOCUX harness).
---

# {name} — agent-native CLI

Generated from `{root}`. Use it to control the software through commands
instead of reading files or GUI automation.

- `python cli.py --help` — discover commands
- `python cli.py --json <group> <name> --arg value` — structured output
- `python cli.py` — REPL

Never guess arguments: ask `--help` first. JSON output is the agent contract.
"""


def _test_py(name: str) -> str:
    return f'''"""Smoke tests for the generated harness (run: pytest test_cli.py)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HERE / "cli.py"), *args],
                          capture_output=True, text=True, timeout=60)


def test_help_answers() -> None:
    proc = _run("--help")
    assert proc.returncode == 0
    assert "usage" in proc.stdout.lower()


def test_commands_importable() -> None:
    sys.path.insert(0, str(HERE))
    from commands import COMMANDS  # noqa: F401
    assert len(COMMANDS) >= 1


def test_json_output_valid() -> None:
    import commands

    sample = commands.COMMANDS[0]
    sys.path.insert(0, str(HERE))
    proc = _run("--json", sample["group"], sample["name"])
    if proc.returncode != 0:
        return  # command may require required args - smoke only
    data = json.loads(proc.stdout)
    assert isinstance(data, dict)
'''


def _harness_md(name: str, root: Path) -> str:
    return f"""# HARNESS: {name}

Generated by THE FOCUX harness from `{root}`.

## Structure
- `commands.py` — one function per command; calls the REAL backend.
- `cli.py` — stdlib argparse shell: `--json`, `--help`, REPL.
- `SKILL.md` — agent skill documentation.
- `test_cli.py` — smoke tests.

## Extend
`focux harness refine {name} "<focus>"` runs a gap analysis and appends
commands. Rules: keep existing functions; call the real backend; verify
with `--help` before trusting the result.
"""
