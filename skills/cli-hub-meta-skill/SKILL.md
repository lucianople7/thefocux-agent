---
name: cli-hub-meta-skill
description: >-
  Discover, install and use agent-native CLIs (CLI-Hub style) for professional
  software — creative, productivity, AI, search. Agents drive real backends
  through structured CLIs with --json output, never pixel-clicking.
  Trigger: "find a CLI for X", "make this software agent-native",
  "install a CLI", "use the real tool for this".
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - CLI_HUB_ENABLED
    bins:
      - python
    emoji: "🛠️"
---

# CLI-Hub Meta-Skill

Agent-native computer use: drive real software through structured CLIs over
real backends (CLI-Anything pattern, Apache-2.0). FOCUX never automates GUIs
by pixel-clicking; it installs and drives CLIs with deterministic JSON output.
Registry and gating live in `policy/focux_cli.py`; installs and spends are
money-gate actions.

## When to use

- User says: "find a CLI for X", "install a CLI", "make this software
  agent-native", "use the real tool", or a task needs professional software
  (docs, image editing, video, search, local LLM).
- Any task where GUI automation would be fragile.

## Steps

### 1. Discover

```python
from policy.focux_cli import CliRegistry
from pathlib import Path
registry = CliRegistry.from_file(Path("references/cli-anything/registry.json"))
hits = registry.search("image")
```

Prefer an existing harness before generating a new one. For a broader catalog
use the live CLI-Hub (`pip install cli-anything-hub`, `cli-hub list/search`).

### 2. Gate the install

Installing tooling is a system change: route through the money-gate
(`install_decision(gate, name)`). At L1 it is REVIEW — human approval card
required before `pip install` / `cli-hub install`.

### 3. Install and verify

Install the harness (`pip install cli-anything-<name>` or `cli-hub install`),
then run `<cli> --help` and one probe command to confirm the backend exists.
Never trust exit 0 alone: verify output (magic bytes, structure).

### 4. Drive it

- REPL (bare command) for interactive sessions; `--json` for machine output.
- Probe before mutate: inspect state before changing it.
- Any invocation that spends money goes through `spend_decision` (MONEY class,
  REVIEW at L1).

### 5. Generate the SKILL.md wrapper (optional)

`render_cli_skill(name, description)` emits the canonical SKILL.md so any
SKILL-compatible shell discovers the CLI. Validate it with
`tools/skill_validator.py`.

## Rules

- CLI-first: never pixel-click when a CLI exists.
- Installs and spends are gated; never bypass the money-gate.
- Use the real backend, never a toy reimplementation.
- Verify output, don't trust exit codes.
