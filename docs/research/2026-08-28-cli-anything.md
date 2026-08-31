# Research: HKUDS CLI-Anything (absorption analysis)

**Date:** 2026-08-28
**Source:** https://github.com/HKUDS/CLI-Anything (Apache-2.0, 48.7k stars, 4.5k forks, 115 contributors)
**Reference copy:** `references/cli-anything/` (cloned 2026-08-28, trimmed to 2.5 MB of text/code, LICENSE preserved)
**Status:** Research complete. Feeds THE FOCUX Agent DNA design (`docs/plans/2026-08-28-thefocux-agent-design.md`).

## 1. What this system is

CLI-Anything turns **any software with a codebase into an agent-native CLI**. Thesis:
*"Today's software serves humans; tomorrow's users will be agents."* It is the
strongest public proof that **CLI beats GUI automation for agents**: no screenshots,
no brittle pixel-clicking, no RPA fragility — structured commands, JSON output, real
software backends, 2,461 passing tests across 18+ professional applications (GIMP,
Blender, LibreOffice, OBS, ComfyUI, n8n, Mailchimp, Exa, Ollama, ...).

Two equally important parts:

1. **CLI-Hub** (`pip install cli-anything-hub`): a registry/package manager of
   ready-made agent-native CLIs (`cli-hub list|search|info|install|update|launch`).
   Each CLI is an independent pip package (`cli-anything-<software>`) with a Click CLI,
   REPL mode, `--json` output, and a generated SKILL.md.
2. **The 7-phase harness generator** (`/cli-anything <path-or-repo>`): Analyze ->
   Design -> Implement -> Plan Tests -> Write Tests -> Document -> Publish. Plus
   `/refine` for gap analysis and incremental coverage. Distributed as plugins for
   Claude Code, Cursor, Codex, OpenClaw, Hermes, Reasonix, etc.

## 2. Why this is exactly what FOCUX needs

The user's core ask: *"un verdadero superagente que pueda moverse y actuar"*
(computer use + browser + business APIs). CLI-Anything is the **reliable
computer-use strategy**: instead of a vision model clicking pixels (fragile, slow,
token-hungry), the agent drives the software's real backend through a structured CLI
with deterministic JSON. This matches our layer's existing CLI-first contract
(`money_gate_cli.py`: `decide|approve`, exit codes 0/1/2, machine-readable).

## 3. Core principles worth absorbing

1. **CLI is the universal agent interface.** Structured, composable, self-describing
   (`--help`), deterministic, JSON-native. A CLI-first layer is agent-native by
   construction — this validates and extends our P0 layer design.
2. **Use the real software, never a toy.** Harness generates valid project files
   (ODF, MLT XML, SVG) and delegates rendering to the real backend (LibreOffice
   headless, blender --background, sox). No Pillow-replaces-GIMP shortcuts.
3. **Output verification, not exit codes.** *"Never trust that export worked because
   it exited 0"* — verify magic bytes, ZIP structure, pixel analysis, RMS levels.
   Same discipline as our receipts/hash-evidence convention.
4. **Dual interaction model.** Stateful REPL for interactive agent sessions +
   subcommand CLI for scripting/pipelines. `--json` everywhere for machine
   consumption, human tables for people.
5. **Probe before mutate.** Every harness starts with probe/info commands so agents
   inspect state before changing it. Maps to our READ-before-write money-gate
   philosophy (READ class is always ALLOW, mutations are gated).
6. **SKILL.md per harness, auto-generated.** Each CLI ships a canonical SKILL.md
   (YAML frontmatter name/description + usage), extracted from Click decorators via
   `skill_generator.py`. This is the same SKILL.md format our layer already uses —
   CLI-Anything proves the pattern at 48.7k-star scale.
7. **The Rendering Gap lesson.** GUI apps apply effects at render time; naive
   exports silently drop them. Native renderer -> filter translation -> render
   script. Deep-domain accuracy beats surface emulation.
8. **Scope installs.** `cli-hub matrix install <name> --capability <id>`, `--dry-run`,
   `--json`, exit codes (0 ok / 3 partial / 1 failure / 2 usage), `--resume`,
   `matrix doctor`. Matches our minimal-install, no-bloat philosophy.

## 4. Skill-by-skill / capability mapping to FOCUX DNA

| CLI-Anything asset | FOCUX module | Verdict | Notes |
|---|---|---|---|
| CLI-Hub registry + `cli-hub` CLI | `focux_cli` (NEW) + fork Capability Marketplace | **Absorb** | Registry of agent-native CLIs; the fork's provider/adapter registries get a CLI-harness category. |
| 7-phase generator (`/cli-anything`) | `focux_cli` generator capability | Absorb (as capability) | Turn any business software (or the user's own tools) into agent-native CLIs. Requires frontier model — gate by model tier. |
| `/refine` gap analysis | `focux_cli` refine | Absorb | Incremental, non-destructive coverage expansion. |
| HARNESS.md SOP (747 lines) | `docs/` methodology | **Absorb** | The definitive how-to for making software agent-native; lessons: real backend, output verification, filter translation, timecode precision, session locking. |
| repl_skin.py | `focux_cli` REPL shell | Adapt | Consistent branded REPL across harnesses. |
| skill_generator.py | Our `tools/skill_validator.py` | Adapt | Auto-generate SKILL.md from Click decorators — we validate, they generate; complement. |
| `cli-anything-exa` | `focux_research` | **Install-ready** | AI-native web search CLI (40 tests) — direct fit for niche-research. |
| `cli-anything-libreoffice` | `focux_docs` (business ops) | Install-ready | Docs/PDF/ODF generation via real LibreOffice — offer sheets, invoices. |
| `cli-anything-comfyui` | `focux_visual` | Install-ready | AI image generation via ComfyUI REST API (70 tests) — complements Gemini prompts. |
| `cli-anything-ollama` | provider universality | Install-ready | Local LLM inference CLI (98 tests) — keyless local option. |
| `cli-anything-mailchimp`, `-n8n`, `-zoom`, `-adguardhome` | business adapters | Install on demand | Email, workflow, comms, network — each gated by money-gate before spend. |
| matrix_registry.json | fork Capability Marketplace | Absorb | Workflow-as-capability packaging (capabilities x providers). |

## 5. What must change for FOCUX (do not copy verbatim)

1. **Money-gating the CLIs.** Installing a CLI = new tooling (gated);
   *running* a CLI that spends (Mailchimp campaign, ComfyUI cloud, Zoom API) is a
   `MONEY`/`COMMERCE`-class action through our money-gate: REVIEW at L1, policy
   delegation at L2, idempotency keys, receipts. CLI-Anything has no spend gate.
2. **Frontier-model requirement.** The generator needs frontier-class models
   (Claude Opus 4.6 / GPT-5.4 class). With Qwen Token Plan, harness generation may
   need manual correction or a dedicated model tier — document this limitation,
   don't promise magic.
3. **Windows-native reality.** CLI-Anything is developed on Linux/macOS; many
   harnesses assume POSIX paths. On Windows native we select CLIs whose backends
   exist on Windows (LibreOffice, ComfyUI, ffmpeg-based) and validate per-harness.
4. **No GUIs needed by default.** FOCUX prefers headless backends; GUI-only software
   (e.g. Sketch) stays out of the core path.

## 6. What this validates about our layer

- **CLI-first is the industry's agent-native answer.** Our `money_gate_cli.py` +
  13 skills follow the same shape as a 48.7k-star project's core thesis.
- **SKILL.md is the universal skill format.** CLI-Anything auto-generates SKILL.md
  for every harness; OpenClaw/CowAgent/Claude Code all read it. Our validator
  (`tools/skill_validator.py`) enforces the same format.
- **Deterministic JSON + exit codes** is the agent contract. Our money-gate CLI
  (exit 0=allow, 1=review, 2=deny) matches CLI-Hub's exit-code discipline.

## 7. Absorption plan into THE FOCUX

- **P0:** `focux_cli` module skeleton (registry-aware: `cli-hub list/search/info`
  wrappers + install gating via money-gate) + `cli-hub-meta-skill` mounted as a
  FOCUX skill (validated by our validator).
- **P1:** install-ready harnesses wired as gated capabilities (exa for research,
  libreoffice for docs, ollama for local inference) in the fork's Capability
  Marketplace; spend-gated via money-gate.
- **P2:** HARNESS.md methodology absorbed into `docs/`; skill_generator.py pattern
  adapted to auto-emit SKILL.md from our CLIs (reverse of our validator).
- **P3:** 7-phase generator as a gated capability for the user's own business
  software (needs frontier-model tier decision).
- **P4:** matrix packaging (workflows as capabilities x providers).

Reference material retained at `references/cli-anything/` (trimmed to methodology +
hub + meta-skill + registries + exa/libreoffice/comfyui harnesses; LICENSE
preserved) so future work can lift exact patterns (REPL skin, skill generator,
registry schema, HARNESS lessons).
