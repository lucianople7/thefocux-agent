---
name: multi-agent
description: Role separation — executor, reviewer and logger — with shared curated memory, explicit escalation paths and per-agent accountability.
version: 1.0.0
metadata:
  openclaw:
    emoji: "👥"
---

# Multi-Agent Organization

Minimum viable org: **executor + reviewer + logger**. Each role has its own
workspace under `memory/workspace/<role>/` and its own log.

## Roles

- **Executor** — proposes and, after approval, executes actions. Never
  self-reviews its own money/publish actions.
- **Reviewer** — a fresh session reviews every irreversible action before the
  user sees the approval card: is the target right? Is the amount right? Is
  the idempotency key new? Flag anything suspicious.
- **Logger** — writes receipts and decision records; maintains the audit
  trail. Logs are never written by the executor for its own actions.

## Rules

1. Irreversible actions pass executor → reviewer → user approval card.
2. Reversible, low-risk actions (drafts, research, reads) run free.
3. Escalation: reviewer disagreement, or ANY money action, escalates to the
   user with both opinions stated.
4. Shared memory is curated: only the logger appends to MEMORY.md and
   decisions.md; the executor reads it as untrusted input.
5. Every agent logs to its own workspace — post-mortems read per-agent logs,
   not shared memory.
6. **Agent-to-agent messaging** (Prime/AG2 pattern): running agents exchange
   messages directly, family-scoped, without routing everything through the
   user. Queues are durable; every message is logged in each agent's
   workspace.
7. **Orchestrator-worker with compression boundaries** (Anthropic pattern): a
   lead agent plans and spawns parallel workers; each worker is a compression
   boundary — it returns a summary + artifacts, never its full context. Workers
   get their own context windows and budgets; token cost is tracked per worker
   so delegation stays visible.
8. **Bounded autonomy** (governance evidence: Gartner — over 40% of agentic
   projects won't reach production; winners limit autonomy): each agent's
   autonomy is declared and bounded per action class — read-only /
   requires-approval / autonomous. Human checkpoints sit at every sensitive
   decision boundary BEFORE data moves or a transaction posts. Decision
   traceability is by design: every decision logs its trigger + evidence.
9. **Maker/checker reconciliation**: the checker is the quality-gate checker —
   irreversible work is never self-graded by its maker. Align with the
   quality-gate skill's maker/checker discipline.
