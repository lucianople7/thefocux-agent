---
name: workflow-stages
description: The stage-gated lifecycle for work that outlives one session — frame, plan, execute, verify, verified — with durable state and a human approval at frame exit.
version: 1.0.0
metadata:
  openclaw:
    emoji: "📋"
---

# Workflow Stages

Work that outlives one session runs through the stage-gated lifecycle:
**frame → plan → execute → verify → verified**. Anything a single session can
finish and verify is done directly — the lifecycle exists for work that must
survive context-window limits, session restarts, and human review.

## Rules

1. **Frame**: write `memory/work/<id>/SPEC.md` containing the objective, the
   scope, the acceptance criteria, and the money/publish implications (if any,
   per the money-gate skill). THE HUMAN APPROVES THE FRAME. No model gate
   stands in for product judgment: the agent never self-approves a frame. Use
   `auto-resume` to re-enter the work from a fresh session.
2. **Plan**: write `memory/work/<id>/PLAN.md` listing the steps, the owner role
   for each step, the verification for each step, and the budgets: max
   iterations, max model calls, max time, max cost.
3. **Execute**: run the plan with bounded execution and circuit breakers. Stop
   on: iteration limit reached, repeated identical failure, repetition/loop
   detected, context budget exhausted, cost threshold crossed. On stop: return
   the partial results, explain what happened, and escalate. Never discard
   completed work.
4. **Verify**: run the quality-gate skill. A deterministic, machine-checkable
   verifier must pass. Maker/checker: the executor never grades its own work.
   The verifier's failure output goes back to the agent for bounded repair.
5. **Verified (terminal)**: write the receipt and mark the work stage
   `verified` in `memory/work/<id>/current.md`. The agent disengages — goes
   quiet — until the next objective.
6. **Durable state**: `memory/work/<id>/` holds `SPEC.md`, `PLAN.md`,
   `current.md` (stage + progress), and `ROADMAP.md` (what comes next). State
   survives context-window limits and session restarts.

## Never

- Never skip the human frame approval — no model gate substitutes for it.
- Never mark work `verified` without a passing gate.
- Never claim completion from memory — verify with the gate and record the
  evidence.
