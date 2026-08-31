# THE FOCUX — Provider-Agnostic & Plugin-Ready Guarantee

**Date:** 2026-08-28
**Scope:** the whole product (kaizen7-jarvis runtime + `focux/` DNA layer)
**Guarantee:** THE FOCUX runs with **any LLM provider, any agent skill/plugin
format, on any host** — and is built for real-world use, not demos.

## 1. Agnosticism contract (what "agnostic" means here)

1. **Any model provider.** The brain and the DNA never hardcode a vendor. The
   runtime resolves providers through a capability-gated registry; when the
   configured provider fails, it crosses to another family instead of dying.
2. **Any skill/plugin.** The runtime consumes the open Agent Skills format
   (`SKILL.md` with `name` + `description`) — the same format Claude Code,
   Cursor, Codex, OpenClaw, CowAgent, `npx skills add`, and the FOCUX layer use.
   Foreign keys are whitelisted, never silently trusted.
3. **Any host.** The DNA layer is pure Python with no framework dependency; the
   runtime runs on Windows, macOS, Linux and headless servers.
4. **Real world.** Proposal-only by default, human approval gates for anything
   that costs money or changes the world, receipts for every executed action.

## 2. Evidence (verified 2026-08-28)

| Claim | Evidence |
|---|---|
| Multi-provider brain | Runtime provider slots: claude-api, openai (+realtime), codex, gemini-family, openrouter, ollama (local, keyless); fallback crosses families |
| Provider registry | `jarvis/kaizen7/providers.py`: hermes (agent_runtime), codex (coding_agent), api (external), cli (local) — proposal-only, cost/privacy/risk annotated |
| Adapter registry | `jarvis/kaizen7/adapters.py`: openai-compatible, generic-http-api, generic-cli-agent, mcp-server, webhook-agent, cloud-agent |
| Agent Gateway | `jarvis/kaizen7/agent_gateway.py`: Agent Passports (capabilities, cost, privacy, risk, auth, approval policy) — dry-run/proposal-only |
| Portable skill loader | `jarvis/skills/portable.py` + `loader.py`: open Agent Skills format, whitelist fields, never adopts triggers/risk/auto-fire from foreign files |
| **17 FOCUX skills load** | `parse_skill()` on all `focux/skills/*/SKILL.md`: **17/17 OK** in the fork runtime loader |
| Deterministic DNA | `focux/policy/*.py`: pure Python, no LLM SDK imports, no framework — runs anywhere |
| Skill format validator | `focux/tools/skill_validator.py`: 17/17 valid (canonical format) |
| Real-world readiness | `--kaizen7-doctor` OK; `--kaizen7-product` READY 100/100; REST API + CLI + web UI |

## 3. How to connect ANY provider

Providers enter through the same contract (no code changes):

1. **API key provider** (OpenAI-compatible, e.g. Qwen Token Plan, Groq, Mistral):
   set the key in the credential manager / env; the runtime's OpenAI-compatible
   adapter talks to it. Cross-family fallback covers outages.
2. **Local / keyless** (Ollama, llama.cpp): point the runtime at
   `http://localhost:11434` or any OpenAI-compatible server; no cloud account.
3. **Custom / private API**: register a connector in the provider registry
   (`proposal-only`, explicit auth method, cost note, capabilities list,
   receipt logging) — no fork, no core edits.

## 4. How to add ANY skill/plugin

Drop a `SKILL.md` folder (open Agent Skills format) into a skills directory:

- The strict schema catches hand-written typos at authoring time.
- Foreign skills fall back to the portable adapter: known fields are read,
  unknown fields are dropped AND named, nothing that grants behavior
  (triggers, risk_policy, auto_fire, execution, requires_tools) crosses over.
- A foreign skill is *instructions the assistant may follow* — never a
  permission grant. All money/publish/account actions still pass the
  money-gate + approval bridge regardless of the skill.

## 5. Real-world safety (the part "agnostic" never suspends)

- Money NEVER auto-approved (falsification test invariant, untainted or tainted).
- Survival tiers change effort, never authorization.
- Self-improvement is evidence-gated, human-reviewed, append-only audited.
- CLI installs/spends gated (ACCOUNT/MONEY class, REVIEW at L1).
- Proposal-only by default: payments, publishing, outbound messages,
  credentials, financial operations, irreversible changes all require approval.
