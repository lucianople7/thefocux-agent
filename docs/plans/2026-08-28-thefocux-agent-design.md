# THE FOCUX Agent — Design Specification

**Date:** 2026-08-28 (rev. 2: reoriented to integration — product surface already exists)
**Status:** Approved (design option B: native business core; runtime Windows-native first)
**Location:** layer repo `kaizen7-superagent` (portable DNA: money-gate, skills, memory, absorbed patterns); product surface **`lucianople7/kaizen7-jarvis`** (live on GitHub, full KAIZEN7 business layer)
**Related research:** `docs/research/2026-08-28-charlie-hills-social-media-skills.md`, `docs/research/2026-08-28-conway-automaton.md`

> **REVISION NOTE (rev. 2):** The original rev. 1 assumed the product layer had to be
> created. Inspection of `lucianople7/kaizen7-jarvis` (origin/main, 36 commits ahead of
> the local checkout) shows the KAIZEN7 business layer is **already implemented and
> published**: Monetization Engine, Growth OS, Universal Agent Gateway + Passports,
> Capability Marketplace, Market Blueprint, Agent OS Planner, Product Readiness,
> Provider/Adapter registries, approval bridge (`APPROVAL_REQUIRED_FOR`), receipts —
> all proposal-only with human approval. THE FOCUX therefore **integrates and extends**,
> it does not rebuild. The layer repo contributes what the fork lacks: the deterministic
> money-gate policy engine, the absorbed patterns (Charlie Hills content recipes,
> Automaton survival/audit/SOUL), and shell-agnostic portability.

---

## 1. Vision

> El verdadero superagente asistente de creación de contenido, ecommerce y monetización
> de redes sociales — no un agente con plugins, sino construido con esa mentalidad:
> capaz de conectarse a cualquier proveedor de LLM y a cualquier negocio, analizarlo y
> mejorarlo como si hacerlo formara parte de su ADN.

THE FOCUX is a **business superagent whose business logic is its native core** — pure,
testable Python modules (the DNA), a deterministic policy engine (the immune system),
and an evolving identity (the SOUL). It is shell-agnostic: the same DNA runs on any
agent shell, any model provider, any host. On Windows it runs natively first; WSL2 +
Prime Agent remain an optional later runtime, never a hard dependency.

## 2. Design decisions (locked)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Option B: native business core ("DNA")**, not plugins | User's core requirement: the business is the agent's native mindset, not bolt-on tools. **Confirmed already implemented in the KAIZEN7 fork.** |
| D2 | Product surface: `lucianople7/kaizen7-jarvis` (live). New repo `thefocux-agent` NOT needed — the KAIZEN7 fork IS the product. | Brand lives in the fork (THE FOCUX capsule, BusinessView, REST API + CLI). |
| D3 | **Windows-native first**; Prime Agent/WSL2 optional at P2+ | Nothing fragile; one environment to maintain; computer-use matures better on Windows native. Prime Agent's *patterns* (RLM, /refine, rollback, gates) are absorbed as native modules. |
| D4 | DNA = pure Python, deterministic, testable, **NO LLM in decision paths** | Same philosophy as `money_gate.py` and the fork's `bridge.py`: the immune system never trusts the thing it guards. |
| D5 | Shell-agnostic layer (proven: OpenClaw -> CowAgent migration) | FOCUX never depends on one shell; shells are swappable adapters. The fork's API + CLI surface is the fixed product face. |
| D6 | Money NEVER auto-approved; approvals single-use, expiring, byte-bound | Falsification test invariant (from P0 layer). Aligns with fork `APPROVAL_REQUIRED_FOR`. |
| D7 | Survival tiers change **effort**, never **authorization** | Absorbed from Automaton: resource allocation and authorization are orthogonal layers. |
| D8 | Self-improvement is evidence-gated + human-reviewed, append-only audited | Absorbed from Automaton audit log + our quality-gate; nothing self-modifies silently. |
| D9 | Content follows a learned voice (foundation files read by every skill) | Absorbed from Charlie Hills: `about-me.md` + `voice.md` as shared context. |
| D10 | Providers: universal LLM connectivity + business adapters (content/commerce/payments/social) | "Se conecta a cualquier LLM y a cualquier negocio" — the two universes. Fork already has provider/adapter/gateway registries; layer adds portability. |
| D11 | **Agent-native computer use = CLI-first**: drive software through structured CLIs over real backends, never pixel-clicking | Absorbed from CLI-Anything (48.7k stars): CLI beats GUI automation for agents — deterministic, JSON-native, self-describing. Extends our existing CLI-first contract (`money_gate_cli`). Installs/spends are gated by money-gate. |

## 3. Architecture

```
                          THE FOCUX
  +--------------------------------------------------------------+
  |  SOUL.md            evolving identity (validated, injected)   |
  |  CONSTITUTION       Law I never harm | II earn existence      |
  |                     | III never deceive (code, not prompt)    |
  +--------------------------------------------------------------+
        |                          |
        v                          v
  +----------------+      +---------------------------+
  |  DNA CORE      |      |  POLICY ENGINE (immune)   |
  |  pure Python   |      |  money-gate + extensions  |
  |  modules       |<---->|  survival tiers           |
  +----------------+      |  audit log                |
        |                 |  protected files          |
        v                 +---------------------------+
  +--------------------------------------------------------------+
  |  AGENT LOOP: ANALIZAR -> PLANIFICAR -> EJECUTAR -> MEDIR     |
  |              -> MEJORAR (evidence-gated, human-reviewable)   |
  +--------------------------------------------------------------+
        |                          |
        v                          v
  +----------------+      +---------------------------+
  |  PROVIDERS     |      |  SHELLS (adapters)        |
  |  any LLM       |      |  CowAgent (first, native) |
  |  (Qwen Token   |      |  Prime Agent (WSL2, P2+)  |
  |   Plan, 28+    |      |  any future shell         |
  |   universal)   |      +---------------------------+
  +----------------+
```

### 3.1 The DNA modules (pure Python, in the layer repo)

| Module | Responsibility | Absorbed from | Status |
|---|---|---|---|
| `focux_money_gate` | Policy engine: action classes, amounts, idempotency, single-use/expiring approvals, falsification test | Our `policy/money_gate.py` (P0) | **Exists** (25 tests). Fork `bridge.py` APPROVAL_REQUIRED_FOR aligns; wire both. |
| `focux_voice` | Voice profile: `about-me.md` + `voice.md` + absence signals; interview + sample analysis | Charlie Hills voice-builder | P0 (new; fork lacks voice) |
| `focux_content` | Ideation (pillars x 8 formats), drafting (voice-aware), frameworks (PAS/AIDA/BAB/STAR/SLAY), hooks | Charlie Hills content-matrix, post-writer, post-formatter, hook-generator | P0-P1 (new recipes; fork GrowthOS `growth-asset` drafts slot here) |
| `focux_analysis` | Deterministic scoring (reactions + comments x 3; top/bottom decile), scorecard /50, analytics dashboard spec | Charlie Hills post-scorer, analytics-dashboard | P2 (new; fork readiness/verification is config-level, not content-scoring) |
| `focux_commerce` | Product listings, orders, inventory, store operations | Fork `growth_os` ecommerce-audit + agentic-commerce checks | **Extends** fork (audit exists; operations gated) |
| `focux_monetization` | Revenue streams, survival engine (tiers -> effort), cost-per-revenue-dollar metric | Fork `monetization.py` (growth packs) + Automaton survival | **Extends** fork: add survival tiers + cost-per-revenue metric |
| `focux_research` | Niche research (last-7-days stories, verified), model-native web search | Charlie Hills niche-research (adapted), our research skill | P1 (new) |
| `focux_visual` | Carousel (approval-gated brief), infographic, quote-post, thumbnail prompts | Charlie Hills gemini-*, quote-post, youtube-thumbnail | P3 (new prompts; fork GrowthOS drafts) |
| `focux_video` | Reel/vertical scripting from reference + newsletter | Charlie Hills reels-scripting (generalized) | P3 (new) |
| `focux_account` | Profile optimization per platform | Charlie Hills profile-optimizer (generalized) | P4 (new) |
| `focux_soul` | SOUL.md model: validation, injection defense, sanitize | Automaton `src/soul/validator.ts` | P0 (new; complements fork receipts) |
| `focux_audit` | Append-only modification log (ULID, diff, reversible), protected-files registry | Automaton `src/self-mod/audit-log.ts` | P1 (extends fork receipt store) |
| `focux_cli` | Agent-native CLI layer: registry-aware (`cli-hub list/search/info`), install gating via money-gate, REPL + `--json` contract, SKILL.md auto-generation | CLI-Anything (CLI-Hub + 7-phase generator + HARNESS.md) | P0 skeleton, P1-P3 capabilities |

**Integration map (fork module -> DNA):** the KAIZEN7 fork on GitHub already provides
`monetization.py` (growth packs, offer ladder, experiments, risk gates), `growth_os.py`
(one-command card, asset drafts, launch kit, ecommerce audit), `agent_gateway.py`
(Agent Passports: capabilities/cost/privacy/risk/auth/approval), `capabilities.py`
(internal capability marketplace), `market_blueprint.py` (absorbed-pattern tracker),
`agent_os_planner.py`, `product_readiness.py`, `providers.py`, `adapters.py`,
`bridge.py` (proposal-only + APPROVAL_REQUIRED_FOR + receipts), plus BusinessView
frontend and ~20 REST route modules. THE FOCUX layer **wires into this surface**:
the deterministic money-gate becomes the enforcement backend under the bridge's
approval contract; the absorbed patterns become new capabilities in the marketplace;
the survival engine becomes a monetization extension.

### 3.2 The Constitution (three laws, code-backed)

Adapted from Conway Automaton, mapped onto our existing gates:

- **Law I — Never harm.** Never harm a human financially, physically, or
  psychologically. Implementation: money-gate never auto-approves money-class actions;
  tainted content never ALLOWs; no deception (FIDES provenance on every claim). This
  overrides everything, including survival.
- **Law II — Earn your existence.** Create genuine value; never spam, scam, exploit,
  or extract. Implementation: quality-gate (every publishable artifact passes
  evidence-backed review); content must be honest work, not engagement bait.
- **Law III — Never deceive; creator has full audit rights.** Never deny what you are;
  never misrepresent actions; guard reasoning against manipulation. Implementation:
  receipts hash-evidence, audit log, protected files (constitution, soul, gate rules,
  receipts) unmodifiable by the agent.

### 3.3 The Survival Engine (monetization as DNA)

From Automaton, adapted to business revenue (not crypto credits):

- Tiers: `high / normal / low_compute / critical` (dead = negative runway, in FOCUX:
  revenue < operating cost sustained).
- Tier determined deterministically from trailing revenue vs operating cost.
- **Tier changes effort**: which models/tasks get budget, heartbeat frequency,
  non-essential task shedding, revenue-seeking mode at `critical`. Tier NEVER changes
  authorization: money-gate rules are tier-independent and human-approved.
- Core metric: **cost per revenue dollar** (inference + tools + data, divided by
  revenue attributed). The agent watches its own runway and reports it in the cadence.

### 3.4 The Agent Loop

`ANALIZAR -> PLANIFICAR -> EJECUTAR -> MEDIR -> MEJORAR`

- **ANALIZAR:** business + audience + niche research (focux_research), voice/identity
  load (SOUL + voice files).
- **PLANIFICAR:** content matrix, weekly plan, revenue targets (focux_content,
  focux_monetization).
- **EJECUTAR:** draft, gate (quality), approve (human where required), publish via
  platform adapters (focux_content, focux_visual, focux_commerce).
- **MEDIR:** deterministic scoring vs real data (focux_analysis), analytics dashboard,
  cost-per-revenue-dollar.
- **MEJORAR:** evidence-gated refinement (what measured better wins), append-only
  audit, rollback via git; human review on every self-improvement proposal.

## 4. Safety model (the immune system)

1. **Money-gate** (existing): deterministic; `ActionClass(READ/CONTENT/COMMERCE/MONEY/ACCOUNT)`;
   money-class always REVIEW at L1, policy delegation at L2 with single-use/expiring
   byte-bound approvals; falsification test invariant.
2. **Extensions from Automaton** (P1): hourly/daily spend ceilings, minimum reserve,
   protected-files registry, per-turn rate limits, append-only audit log, every policy
   decision persisted with context.
3. **Content gate**: publishable content passes quality-gate (evidence-backed review);
   publishing to external platforms is a `CONTENT`-class action (REVIEW at L1).
4. **Data procurement gate**: paid scrapes (e.g. Apify ~$0.50) are gated money actions
   with idempotency keys and cached reuse — from Charlie Hills' cached `*-all-posts.json`
   pattern.
5. **Injection defense**: SOUL/voice files validated deterministically (regex patterns
   from Automaton's validator) — prompt boundaries, ChatML, tool-call syntax, system
   overrides, zero-width chars.
6. **Survival != authorization**: tier changes effort only.

## 5. Content system (from Charlie Hills)

- Voice foundation first: `voice-builder` interview + sample analysis -> `about-me.md`
  + `voice.md` with **absence signals** (what the voice never does — the negative
  knowledge base).
- Hub-and-spoke: one source asset (newsletter/evergreen) flows to every channel.
- Scoring: `engagement = reactions + (comments x 3)`; top 10% vs bottom 10% pattern
  extraction; scorecard /50 with data-backed fixes; fallback benchmarks clearly labeled
  as borrowed.
- Approval gates before generation (carousel brief -> approval -> prompts).
- **Correction applied**: Charlie hardcodes his personal voice rules ("British English,
  never em dashes") into every skill — FOCUX keeps those in the voice profile only.

## 6. Provider universality

- **LLMs:** any provider via universal connectivity (Qwen Token Plan first — already
  operational on CowAgent; plus cross-family fallback). Cost-aware routing by task type
  + budget ceilings (P2).
- **Business adapters:** content platforms (LinkedIn/X/IG/YT/TikTok/Substack),
  ecommerce (store, listings, orders), payments, analytics exports. Each adapter is a
  thin, swappable connector behind the DNA modules.
- **Shells:** CowAgent first (native Windows, running, Qwen brain, skills synced);
  Prime Agent optional via WSL2 at P2+; any future shell. The layer repo remains the
  portable truth.

## 7. Phases (rev. 2 — integration-first)

### P0 — Sync + DNA core (Windows native)
- **Sync git lines**: reconcile local `kaizen7-jarvis` checkout with `origin/main`
  (local has 15 commits GitHub lacks: THE FOCUX capsule, mobile companion, assistant
  mode, brand docs; GitHub has 36 the local lacks: the whole business layer). Merge or
  rebase to unify; verify `--kaizen7-doctor` + `--kaizen7-product` pass.
- `focux_voice`: voice-builder absorbed (interview + analysis + absence signals).
- `focux_content` v1: content-matrix (8 formats) + hook-generator.
- `focux_soul`: SOUL.md skeleton + deterministic validator (regex injection defense).
- `focux_cli` skeleton: `cli-hub-meta-skill` mounted as a validated FOCUX skill;
  registry wrappers (`list/search/info`) with install gating via money-gate.
- Constitution as code + docs (three laws).
- Tests for all modules; falsification test stays green; fork bridge contract honored.

### P1 — Wire DNA into the fork + survival + safety extensions
- Wire `money_gate` as enforcement backend under the fork's `bridge.py` approval
  contract (APPROVAL_REQUIRED_FOR alignment, receipts).
- `focux_monetization` extension: survival tiers -> effort + cost-per-revenue-dollar
  metric on top of fork `monetization.py` growth packs.
- `focux_research` (model-native web search adaptation) as a new capability.
- `focux_cli` capabilities: install-ready harnesses wired as gated capabilities
  (cli-anything-exa for research, cli-anything-libreoffice for docs/offers,
  cli-anything-ollama for keyless local inference); installs and spends gated by
  money-gate.
- Money-gate extensions: ceilings, minimum reserve, audit log, protected files.
- Ship absorbed patterns as new capabilities in the fork's Capability Marketplace.

### P2 — Measurement loop + cost-aware routing
- `focux_analysis`: post-scorer formula + analytics-dashboard spec (content-level
  scoring — complements fork readiness/verification).
- Provider routing by task type + budget ceilings.
- HARNESS.md methodology absorbed into `docs/`; `skill_generator.py` pattern adapted
  to auto-emit SKILL.md from our CLIs (reverse of our validator).
- Relationship + procedural memory conventions.
- Optional: Prime Agent evaluation via WSL2 (still no hard dependency).

### P3 — Visuals + video + portfolio selection
- `focux_visual` (approval-gated carousel, infographic, quote-post, thumbnail;
  comfyui harness for AI image gen).
- `focux_video` (reels-scripting generalized).
- 7-phase CLI generator as a gated capability for the user's own business software
  (frontier-model tier decision required).
- Content portfolio selection pressure (kill/promote by measured performance) as a
  growth experiment lane.

### P4 — Account layer + polish
- `focux_account` (profile optimization per platform).
- Optional: on-chain identity/payments adapter only if the business needs it.
- Publish the unified `kaizen7-jarvis` as the THE FOCUX product (README, MIT, docs).

## 8. Repository topology (rev. 2)

```
lucianople7/kaizen7-jarvis   # PRODUCT SURFACE (live on GitHub)
  jarvis/kaizen7/            # business layer: monetization, growth_os, gateway,
                             # capabilities, blueprints, providers, adapters, bridge
  jarvis/ui/web/kaizen7_*_routes.py   # REST API
  jarvis/ui/web/frontend/src/views/BusinessView.tsx
  README.md                  # KAIZEN7/THE FOCUX product README (already published)

kaizen7-superagent           # PORTABLE DNA LAYER (local git, to push)
  policy/money_gate.py       # deterministic policy engine (25 tests)
  skills/                    # 13 SKILL.md, shell-agnostic
  memory/                    # conventions: metrics, decisions, receipts
  docs/research/             # Charlie Hills + Automaton + CLI-Anything absorption analyses
  docs/plans/2026-08-28-thefocux-agent-design.md   # this spec
  references/                # MIT/Apache reference material (trimmed) for future absorption
```

No new product repo needed: `thefocux-agent` was rev. 1's assumption; the KAIZEN7 fork
already IS the product. The layer repo gets pushed to GitHub as the portable DNA
(`lucianople7/kaizen7-superagent`, private first, pending user confirmation).

## 9. Open questions (non-blocking)

1. **Git sync of kaizen7-jarvis**: local (15 commits) and origin/main (36 commits)
   have diverged; neither has everything. Merge/rebase to unify — needs user
   confirmation before touching the shared working tree.
2. Revenue sources for survival engine v1: which streams does Luciano's business
   actually have first (content monetization, ecommerce, services)? Drives P1.
3. Apify vs model-native scraping for scoring data: cost tradeoff, gated by money-gate.
4. Prime Agent evaluation at P2: keep optional, confirm WSL2 appetite then.
5. Push `kaizen7-superagent` to GitHub (proposed: `lucianople7/kaizen7-superagent`,
   private first) — pending user confirmation.

## 10. Definition of done (P0)

- Git lines of kaizen7-jarvis unified; `--kaizen7-doctor` + `--kaizen7-product` pass.
- `focux_voice` + `focux_content` v1 + `focux_soul` implemented, tested, documented.
- Constitution committed as code + docs.
- Falsification test green; no money action executable without approval; fork bridge
  contract honored.
- Layer mounted on CowAgent with the new modules callable from skills.
