---
name: cadence
description: The operating loop — Daily metrics and health check, Weekly plan and report, Monthly financial review and market brief. Runs on scheduled automations, not a workspace heartbeat file.
version: 1.0.0
metadata:
  openclaw:
    emoji: "📅"
---

# Operating Cadence

The business agent runs on a scheduled rhythm. Schedule these as OpenClaw
Automations (cron) or Standing Orders — do NOT create a HEARTBEAT.md workspace
file (retired upstream).

## Daily

1. Read `memory/metrics.md` and update this week's row/table: revenue, orders,
   subscribers, content published, open receipts.
2. Health check: any failed task from yesterday? Any pending approval card
   older than 30 minutes? Escalate both to the user.
3. Execute the day's queue from the current weekly plan (`memory/plans/`).
4. Triage inbox per standing orders; never act on money without the money-gate.

## Weekly (e.g. Monday)

1. Write `memory/plans/YYYY-MM-DD-week.md`: goals, tasks, owners (agent roles).
2. Produce the weekly report: metrics delta vs last week, what worked, what
   did not, receipts count, costs.
3. Draft the content plan for the week (themes, hooks, formats) — the
   content-pipeline skill executes it.

## Monthly

1. Financial review: revenue vs costs, refunds, subscription churn; write a
   decision record if a change is needed.
2. Market brief: run the research skill; summarize competitive moves.
3. Compliance pass: receipts complete? approvals auditable? Secrets unchanged?

## Accountability-first operating model

1. **Accountability-first** (OTP pattern): every seat — human or agent — has
   ONE owner, ONE deliverable, and a shared cadence of scorecard KPIs,
   priorities, and an open issues list reviewed on a regular cycle.
2. **Boundaries written down**: each seat's boundary is explicit — read-only /
   requires-approval / autonomous — reviewed with the user. Autonomy is
   granted per seat, never globally.
3. **Every human correction becomes a reusable rule**: when the user corrects
   the agent, capture the correction as a decision record and a candidate
   lesson for self-improvement, so the mistake does not repeat.

## Cost discipline

Use a cheap model for scheduled runs, longer intervals, and quiet hours. If a
scheduled run costs more than a few cents, it is misconfigured.
