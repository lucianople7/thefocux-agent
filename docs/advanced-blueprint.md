# KAIZEN7 Superagent — Advanced Blueprint (P2–P6)

## 1. Vision

The KAIZEN7 Superagent is an always-on business operator — content, commerce,
sales, research — that is superior to any single existing agent because it
absorbs the best patterns of the 2026 agent ecosystem instead of re-inventing
them. Every absorbed pattern carries provenance (the superiority map in
README.md), runs behind a deterministic control plane, and treats money safety
as a hard boundary. The superagent is shell-agnostic: it runs on OpenClaw
today, uses DeepSeek Harness as a dev lab, and can move to QwenPaw when that
shell matures.

## 2. Layers (0–7)

| Layer | Content |
| --- | --- |
| 0 — Shell | OpenClaw today, DeepSeek Harness as dev lab, QwenPaw future |
| 1 — Work lifecycle | Stage-gated lifecycle frame -> plan -> execute -> verify -> verified (`skills/workflow-stages`) |
| 2 — Deterministic control plane | Budgets, circuit breakers, quality gates, maker/checker |
| 3 — Money safety | Provenance + parameter-level auth + short-lived credentials + point-of-sale enforcement + out-of-band HITL + tamper-evident audit (`policy/money_gate.py`, `skills/money-gate`, `skills/commerce-ops`) |
| 4 — Memory | Tiered, versioned, quarantined, knowledge-graph-backed (`skills/business-memory`, `skills/knowledge-graph`) |
| 5 — Meta-skills | Evidence-gated self-improvement, idle post-session review (`skills/self-improvement`, `skills/idle-review`) |
| 6 — Execution | Content, commerce, sales, research, cadence, multi-agent (`skills/content-pipeline`, `skills/commerce-ops`, `skills/sales-qualification`, `skills/research`, `skills/cadence`, `skills/multi-agent`) |
| 7 — Governance outer loop | Identity, registry, bounded autonomy, decision traceability |

## 3. P2–P6 phases

- **P2 — Content engine**: Qwen-Image / Wan / Remotion / Postiz with a human
  signature gate before anything publishes (`skills/content-pipeline`).
- **P3 — Commerce + payments**: Saleor + Stripe MCP, parameter-level auth,
  agent payment credentials, and the Budget Reservation protocol — the
  industry-convergent gap our money-gate fills (agent-payments-landscape).
- **P4 — Action bodies**: browser allowlist, computer-use per-app, sandboxed
  code execution (microVM / gVisor, never the local executor).
- **P5 — Cadence live + durable execution**: Temporal for HITL workflows with
  checkpoint-resume (`skills/cadence`).
- **P6 — L2 policies + A2A/ACP + voice**: Qwen3-Omni voice, OTel GenAI tracing,
  eval-driven CI gates (golden datasets, shadow/canary, auto-rollback).

## 4. Non-negotiables

- Money-gate determinism + falsification: no LLM ever decides a money action;
  with the gate off, the agent must not move money.
- Tainted content never auto-approves.
- Self-improvement is evidence-gated and human-reviewed.
- Completion only via machine-checkable gates.
- Supersede-not-delete (quarantine, typed retention).
- Bounded autonomy.

## 5. Sources

- Prime Agent — https://arxiv.org/abs/2608.23552
- Continual Harness — https://arxiv.org/abs/2605.09998
- FIDES (argument-level provenance) — https://arxiv.org/abs/2605.11039
- CISA joint advisory on securing agentic AI — https://www.cisa.gov/news-events/news/cisa-us-and-international-partners-release-guide-secure-adoption-agentic-ai
- OWASP Agentic AI Top 10 — https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/
- RLM (recursive language models) — https://arxiv.org/abs/2512.24601
- Misevolution (ICLR 2026) — https://arxiv.org/abs/2509.26354
- Compaction Cliff — https://arxiv.org/abs/2608.22752
- Agent payments landscape — https://www.politesi.polimi.it/handle/10589/260157
