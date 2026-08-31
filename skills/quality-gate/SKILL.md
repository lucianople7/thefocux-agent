---
name: quality-gate
description: A task is complete only when a machine-checkable verifier passes — never on the model's own opinion. Maker/checker discipline for every completion claim.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🎯"
---

# Quality Gate

A task is complete only when a machine-checkable verifier passes. The model's
own opinion is never evidence of completion.

## Principle

An automated loop may only complete work when a user-defined, machine-checkable
gate passes. A passed gate checks only what that gate verifies; reaching a
limit does not imply task success.

## Rules

1. **Maker/checker**: the executor (maker) produces; a separate reviewer
   (checker) — a different model/context — verifies the work against the
   acceptance criteria. The optimizer never grades its own work.
2. **Deterministic verifiers first**: use scripts, assertions, schema checks,
   and receipt checks. LLM-as-judge is allowed only where deterministic checks
   are impossible, and only with a rubric — never a bare "looks good".
3. **On gate failure**: feed the failure output (not a summary) back to the
   maker for bounded repair — max N retries, then escalate to the human.
4. **Regression discipline**: if a change regresses a previously passing gate,
   roll back the change, never the gate.
5. **Integration**: the workflow-stages skill calls this at the Verify stage;
   the money-gate rules apply to money/publish actions inside the work.

## Never

- Never mark work complete without a passing gate.
- Never let the maker self-verify irreversible work.
- Never weaken a gate to make it pass.
