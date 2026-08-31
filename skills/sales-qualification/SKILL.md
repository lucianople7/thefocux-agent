---
name: sales-qualification
description: Disqualifier-first lead qualification with state-machine follow-up and human-reviewed outreach — hybrid human-AI, never autonomous cold outreach.
version: 1.0.0
metadata:
  openclaw:
    emoji: "💰"
---

# Sales Qualification

Qualify leads, manage follow-up, and prepare outreach. The agent DRAFTS; a
human reviews and personalizes before anything is sent. Autonomous cold
outreach is a documented collapse (AI-SDR churn 50-70%) — never send
autonomously.

## Rules

1. Disqualifier-first: ask only questions whose answers could STOP the deal
   (budget, authority, need, timing, fit). Everything else is context. If a
   disqualifier triggers, stop and document why.
2. State machine, not cadence: each lead has a state (new → qualified →
   proposed → negotiating → won/lost; or disqualified). Follow-up depends on
   state and signal, not a fixed cadence; a static cadence on disinterested
   leads is a documented failure.
3. Availability before qualification: offer availability early — availability
   creates momentum.
4. Hybrid human-AI outreach: the agent drafts the message; a human reviews and
   personalizes before anything is sent. Never send autonomously.
5. Deterministic discipline: name exact fields (the agent must not guess which
   field); filter with tags, not prompt instructions; anything that can be
   deterministic, make deterministic.
6. Money gate: any quote, discount, or payment action is a COMMERCE/MONEY
   action — route through the money-gate skill. Qualification never authorizes
   money movement.

## Never

- Send outreach without human review.
- Chase leads past a disqualifier.
- Invent deal stage transitions without evidence — log the trigger for every
  transition.
- Let the agent promise pricing without approval.
