# Research: Agent catalogs (absorption analysis)

**Date:** 2026-08-28
**Sources (all cloned to `references/` for future work):**
1. `ashishpatel26/500-AI-Agents-Projects` — 500+ use cases across industries, 21 runnable agents
2. `jim-schwoebel/awesome_ai_agents` — 1,500+ resources: apps, frameworks, security, testing
3. `Shubhamsaboo/awesome-llm-apps` — 100+ clone-ready apps, **Apache 2.0**, single-file Python
**Status:** Research complete. Feeds THE FOCUX product (kaizen7-jarvis `focux/`).

## 1. What these catalogs are

Three complementary discovery layers for agent-native software:

- **500-AI-Agents-Projects**: practical, runnable reference agents per industry
  (web research, email drafting, social media, stock research, competitive
  analysis, customer support...). Good for *case-shape* inspiration.
- **awesome_ai_agents (jim-schwoebel)**: the biggest index — categories like Ads
  AI Agents, AI Shopping Agents, Content Creation, Digital Workers, AI Security,
  Agent Memory. Good for *coverage mapping* (what exists in each niche).
- **awesome-llm-apps (Shubhamsaboo)**: the actionable one — **Apache 2.0,
  single-file Python apps** that can be cloned, adapted, and mounted behind the
  FOCUX gates. This is the "coge lo mejor" goldmine for production recipes.

## 2. Verdict on licensing and reuse

- awesome-llm-apps: Apache 2.0 — compatible with our MIT product and the layer's
  "absorb patterns, cite sources" rule. Single-file apps (one `.py` + README) make
  them ideal for adaptation into `focux_*` modules or fork capabilities.
- 500-AI-Agents-Projects: individual agents have their own licenses; treat as
  pattern references, not vendorable code.
- awesome_ai_agents: a link index only (no code to copy).

## 3. Most relevant apps for THE FOCUX (map to DNA)

| awesome-llm-apps app | FOCUX module / capability | Verdict | Notes |
|---|---|---|---|
| `ai_email_gtm_outreach_agent` | `focux_sales` / Growth OS outreach lane | **Absorb** (pattern) | Multi-agent B2B outreach: company finder (Exa), contact finder, research, tailored emails. In FOCUX: proposal-only; sending = `MONEY`/`CONTENT` REVIEW. |
| `ai_consultant_agent` | `focux_analysis` ANALIZAR phase | Absorb | Market analysis + strategic recommendations with real-time web research. Feeds the ANALIZAR step of our loop. |
| `product_launch_intelligence_agent` | Growth OS launch kit | **Absorb** | Streamlit hub turning public-web data into launch insights; 3-agent coordinated team (Agno). Matches fork `launch-kit` surface. |
| `ai_data_analysis_agent` + `ai_data_visualisation_agent` | `focux_analysis` MEDIR | Absorb | Data analysis + visualization — complements our post-scorer/analytics dashboard. |
| `ai_agent_governance` | Policy engine extensions | **Absorb** | Deterministic governance: action interception BEFORE execution, audit logging, FS guards, network allowlist, rate limiting. **Validates and extends our money-gate** — same architecture (pre-execution policy). |
| `multi_agent_trust_layer` | `focux_audit` + fork Agent Gateway | **Absorb** | Agent identity with human sponsor, trust scoring 0-1000, delegation chains, policy enforcement, audit trail. Directly extends the fork's Agent Passports. |
| `ai_self_evolving_agent` | `skills/self-improvement` | Reference | EvoAgentX-style: goal -> generated multi-agent workflow -> code -> verify/repair. Matches our evidence-gated improvement (we keep human review as hard gate). |
| `ai_customer_support_agent` | `focux_commerce` support | Reference | Support automation pattern; adapt with money-gate on refunds. |
| `always_on_hn_briefing_agent` / `release_radar_agent` | cadence / research | Reference | Always-on briefing patterns for our cadence skill. |
| `xai_finance_agent`, `ai_investment_agent`, `ai_personal_finance_agent` | `focux_monetization` | **Reject or gate hard** | Finance apps handle real money flows; in FOCUX all financial operations stay `MONEY`-class REVIEW. Pattern reference only. |
| `ai_meme_generator_agent_browseruse` | `focux_visual` | Reference | Browser-use based generation; FOCUX prefers CLI-first (D11). |

## 4. 500-AI-Agents-Projects: case shapes worth noting

Runnable agents in `agents/` that map to FOCUX surfaces:
- `14-social-media-agent` -> `focux_content` distribution
- `05-email-drafting-agent` -> Growth OS asset drafts
- `08-data-analysis-agent` -> `focux_analysis`
- `11-stock-research-agent` -> monetization research (pattern)
- `19-competitive-analysis-agent` -> `focux_research` ANALIZAR
- `21-pii-sanitization-agent` -> **Law III / injection defense** (privacy scrub)

## 5. What this validates about THE FOCUX

- **Pre-execution policy governance is the industry norm.** `ai_agent_governance`
  (action interception, audit, allowlists, rate limits) and `multi_agent_trust_layer`
  (identity, trust scores, delegation, audit) confirm our money-gate + bridge.py
  architecture is exactly where the ecosystem is going.
- **Single-file, clone-ready apps (Apache 2.0) are the fastest absorption path.**
  Our layer can adapt them into `focux_*` modules or fork capabilities behind the
  existing gates — no framework adoption, no new runtime.
- **We already cover the top categories** (content creation, customer service,
  data analysis, email, governance) with our 17 skills + 19 fork capabilities;
  the catalogs add *recipes*, not missing pillars.

## 6. Absorption plan

- **P1:** adapt `ai_agent_governance` extensions (network allowlist, rate limits)
  into money-gate policy; `ai_data_analysis_agent` -> `focux_analysis` scoring.
- **P2:** `product_launch_intelligence_agent` -> fork launch-kit capability;
  `ai_email_gtm_outreach_agent` pattern -> proposal-only outreach lane (sending
  gated).
- **P3:** `multi_agent_trust_layer` trust scoring -> fork Agent Passports.
- **P4:** `ai_self_evolving_agent` as *reference only* — our self-improvement stays
  evidence-gated with human review.

Reference clones retained (trimmed where needed) under `references/` so future
absorption can lift exact single-file recipes.
