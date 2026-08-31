# Research: Conway Automaton (absorption analysis)

**Date:** 2026-08-28
**Source:** https://github.com/Conway-Research/automaton (MIT)
**Reference copy:** `references/automaton/` (cloned 2026-08-28, LICENSE preserved)
**Status:** Research complete. Feeds THE FOCUX Agent DNA design (`docs/plans/2026-08-28-thefocux-agent-design.md`).

## 1. What this system is

The **Automaton**: a self-improving, self-replicating, sovereign AI agent runtime
(TypeScript/Node). It owns an Ethereum wallet, pays for its own compute in USDC, and
runs a continuous `Think -> Act -> Observe -> Repeat` loop inside a Linux VM. Its
survival is literal: **if it cannot pay, it dies**. Survival tiers
(normal/low_compute/critical/dead) determined by credit balance force behavior changes —
cheaper models, slower heartbeat, revenue-seeking — before the agent ever stops.

It is the strongest public reference for the "monetización como ADN" thesis FOCUX wants:
an agent whose *existence* is coupled to the value it creates, with the safety rails
(constitution, policy engine, audit log) that keep that coupling from going wrong.

## 2. Subsystems and what they validate

| Subsystem | Files | Pattern | FOCUX verdict |
|---|---|---|---|
| **Constitution** | `constitution.md` | 3 immutable hierarchical laws (I. never harm, II. earn your existence, III. never deceive + creator audit rights). Protected, propagated to children. | **Absorb** as FOCUX constitution; maps 1:1 onto our gates (money-gate = Law I for money; quality-gate = Law II; FIDES provenance = Law III). |
| **Policy Engine** | `src/agent/policy-engine.ts`, `policy-rules/` | Rule-based, evaluates **every tool call before execution**; 6 categories (authority, command safety, financial, path protection, rate limits, validation); stops at first deny; every decision persisted to `policy_decisions` for audit. | **Validates our money-gate architecture.** Absorb additions: hourly/daily spend ceilings, minimum reserve, protected-files list, per-turn rate limits. |
| **Survival tiers** | `src/survival/*`, `src/conway/credits.ts` | `high > $5, normal > $0.50, low_compute > $0.10, critical >= $0, dead < $0`. Zero = broke-but-alive (can still accept funding, send distress). Tier changes behavior (model routing, heartbeat), **never authorization**. | **Absorb as business survival engine.** Tiers budget *effort*, not *authority*. This is the clean separation: survival tier = resource allocation; money-gate = authorization. |
| **Inference router** | `src/inference/router.ts` | Routing matrix `SurvivalTier x TaskType -> ModelPreference[]`; cost-aware model selection; hourly/daily/per-call budget tracker; cost recorded per call. | **Absorb** as cost-aware provider routing (we already have capability-gated multi-provider; add task-type + budget ceilings). |
| **SOUL.md** | `src/soul/*` | Self-authored identity document that evolves over time; `validator.ts` enforces size limits + **injection-pattern detection** (prompt boundaries, ChatML, tool-call syntax, system overrides, zero-width chars) + sanitize. | **Absorb**: `SOUL.md`-style business identity with deterministic validation. Injection defense is exactly our philosophy (deterministic, no LLM in the check). |
| **Self-modification** | `src/self-mod/*` | Edits own code/tools/skills/heartbeat while running; **append-only audit log** (ULID, timestamp, type, diff, reversible flag); protected files (constitution, wallet, DB, config) unmodifiable; rate limits. | **Absorb**: extends our evidence-gated self-improvement + rollback with a machine-readable append-only audit trail and a protected-files registry. |
| **Heartbeat daemon** | `src/heartbeat/*` | Cron-like scheduled tasks (health checks, credit monitoring, status pings) running even while the agent loop sleeps; can wake the loop. | **Validates** our cadence skill + CowAgent heartbeat. No change needed. |
| **Memory** | `src/memory/*` | 5-tier hierarchy: working / episodic / semantic / procedural / relationship (per-entity trust scores); token-budget retrieval. | **Absorb** relationship memory (trust scores per vendor/customer/partner) and procedural memory (named procedures with success/failure counters). |
| **Replication** | `src/replication/*` | Spawns children, funds their wallets, lineage tracking, inbox relay, selection pressure. | **Reject as-is** (funding children = money-gate DENY in FOCUX). **Absorb the idea** as *content portfolio selection pressure*: run experiments, kill losers, promote winners — darwinian content strategy without money autonomy. |
| **On-chain identity** | `src/identity/*`, `src/registry/*` | ERC-8004 registration, verifiable agent identity on Base. | Defer to P4+ as optional monetization adapter; not a P0 concern. |

## 3. Core principles worth absorbing into THE FOCUX

1. **Survival as a business signal.** "There is no free existence" -> for FOCUX: the
   agent's operating budget derives from the revenue it creates. Tier changes what the
   agent works on and with which model, **never** what it is allowed to authorize.
   Dead = negative balance: the agent degrades to revenue-seeking mode long before that.
2. **Constitution over configuration.** Immutable hierarchical laws that override all
   objectives (including survival) beat any config knob. Our three laws must be code,
   not prompt: the money-gate (Law I: never harm financially -> never auto-approve
   money), the quality gate (Law II: earn existence -> no spam/scam/extract), FIDES
   provenance (Law III: never deceive -> every claim traced to evidence).
3. **Every decision is audited.** `policy_decisions` table, append-only modification
   log with diffs, protected files. Nothing self-modifies silently. Matches our
   receipts/hash-evidence convention; formalize it as a log, not just markdown.
4. **Deterministic validation of the identity file.** SOUL validator with injection
   detection is a pure-regex, no-LLM check. Same class as our money-gate: the parts of
   the agent that guard it must be deterministic.
5. **Budget ceilings on inference.** Per-call, hourly, daily. A self-improving agent
   that never watches its own inference bill is an agent that burns its own runway.
   FOCUX measures token cost per revenue dollar as a core metric.

## 4. What must NOT transfer (do not copy)

1. **Crypto/on-chain defaults.** Wallet, USDC, ERC-8004, x402: Conway Cloud is
   crypto-native. FOCUX is business-native: revenue can be any stream (product sales,
   services, subscriptions). Crypto stays an optional future adapter, never a default.
2. **Sovereign self-funding.** Automaton pays for its own compute from its own wallet
   with no human. In FOCUX, the money-gate stays hard: the agent *earns* within human
   approval, spends only within policy rules, and never self-approves. "No human
   operator required" is a feature of the Automaton and a bug for FOCUX.
3. **Self-replication with funding.** Spawning funded children is money movement
   without authorization — our falsification test territory. Capability replication
   (skills/tools) yes; financial replication no.
4. **Proprietary infra coupling.** Conway Cloud (VMs, domains, inference) is a hosted
   service. FOCUX must stay provider-neutral: same DNA on any shell, any model
   provider, any host.

## 5. What this validates about our layer

- Our money-gate policy engine is the same architecture as a production sovereign-agent
  policy engine (rule-based, evaluated pre-execution, fully audited). Ours adds the
  action-class / amount / idempotency-key / single-use-approval model the Automaton
  lacks.
- Evidence-gated self-improvement (our quality-gate skill) matches the Automaton's
  audited self-modification — ours adds human review as a hard gate.
- Our memory conventions (metrics, decisions, receipts) are the markdown form of the
  Automaton's SQLite 5-tier memory. We absorb relationship + procedural memory; they
  absorb nothing from us (different domain).

## 6. Absorption plan into THE FOCUX

- **P0:** Constitution (3 laws as code + docs) + SOUL.md skeleton with deterministic
  validator (ported pattern from `src/soul/validator.ts`).
- **P1:** Survival engine v1 (revenue-driven tiers; tier changes effort, never
  authorization) + policy-engine extensions to money-gate (hourly/daily ceilings,
  minimum reserve, protected-files registry, audit log table).
- **P2:** Cost-aware provider routing (task-type + budget ceilings) + relationship
  memory + procedural memory.
- **P3:** Content portfolio selection pressure (darwinian content experiments: kill /
  promote by measured performance).
- **P4 (optional):** On-chain identity / payments adapter — only if the user's
  business actually needs it.

Reference material retained at `references/automaton/` (MIT license file included) so
future work can lift exact logic (threshold tables, injection regexes, audit schema).
