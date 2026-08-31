# Research: Charlie Hills social-media-skills (absorption analysis)

**Date:** 2026-08-28
**Source:** https://github.com/charlie947/social-media-skills (MIT, 3.0k stars, 685 forks)
**Reference copy:** `references/social-media-skills/` (cloned 2026-08-28, LICENSE preserved)
**Status:** Research complete. Feeds THE FOCUX Agent DNA design (docs target: `docs/plans/2026-08-28-thefocux-agent-design.md`).

## 1. What this system is

The complete skill system behind Charlie Hills' content machine: 430k+ followers across
LinkedIn, Instagram, Substack, X and YouTube, 100m+ views per year. It is a **hub-and-spoke
content engine**: one newsletter (the source) flows into every other channel, and every
piece of content is written in a single learned voice.

17 Claude Code skills, MIT licensed. Each skill is a `SKILL.md` with trigger phrases,
inputs, and rules. Packaged as a Claude Code plugin (`.claude-plugin/marketplace.json`,
version 1.0.1) and validated by `validate-skills.sh`.

## 2. Architecture pattern (the gold)

```
               voice-builder
        about-me.md + voice.md
        (read by EVERY skill first)
                   |
            newsletter-voice
        newsletter-voice.md
        (the source every piece comes from)
                   |
   +-------+-------+-------+-------+-------+
   |       |       |       |       |       |
Profile LinkedIn Video  Analytics Community Standalone
  |         |       |       |       |       |
profile- post-    reels-  post-   pinned- hook-
optimizer writer  scripting scorer  comment generator
          graphic- youtube- analytics-      content-
          designer thumbnail dashboard     matrix
          post-formatter                    niche-research
                                            gemini-*
                                            quote-post
```

Three layers: **voice foundation** (who you are + how you write), **channel producers**
(one skill per output), **measurement** (scoring + analytics feeding back into production).

## 3. Core principles worth absorbing into THE FOCUX

1. **Voice-first foundation.** Every skill checks `about-me.md` + `voice.md` before
   drafting a line. One learned identity, zero per-skill duplication.
2. **Absence signals.** The voice profile records not only how the voice writes but what
   it *never* does (0-of-5 samples absence): no em dashes, no tricolons, no hashtags.
   This is a negative knowledge base — cheap to build, powerful to enforce.
3. **Hub-and-spoke content.** One source asset (newsletter) repurposed into every channel.
   No channel reinvents the wheel; each adapts the same core.
4. **Deterministic scoring.** `engagement = reactions + (comments x 3)`. Top 10% vs
   bottom 10% pattern extraction. 5 criteria x 10 = /50 scorecard. Scores are
   data-backed: *"Never score higher than 8 unless the draft genuinely matches top 10%
   patterns."* Fixes reference data, never generic advice: *"your top 10% posts use
   number-led hooks (42% of hits). This draft uses a question hook (12%). Lead with the
   stat instead."*
5. **Fallback benchmarks.** When the user has no data, score against published benchmarks
   (Charlie's: avg engagement 1,872, number-led hooks 31%, top length 180-250 words),
   clearly labeled as borrowed data.
6. **Approval gates before generation.** `gemini-carousel` builds a design brief and
   waits for explicit user approval *before* emitting image prompts. Same philosophy as
   our money-gate: REVIEW then act.
7. **Numbers, not adjectives.** *"Engagement rate is 2.3%" beats "engagement is healthy".*
8. **Skill validation in CI.** `validate-skills.sh` checks skills against a spec — the
   same idea as our `tools/skill_validator.py`. Confirms our layer model is
   industry-standard, not idiosyncratic.
9. **Surface-aware output.** The same skill renders differently per surface (interactive
   widget vs file vs inline table). Portability lesson: logic in the skill, rendering in
   the adapter.

## 4. Skill-by-skill mapping to FOCUX DNA

| # | Charlie skill | FOCUX module | Verdict | Notes |
|---|---|---|---|---|
| 1 | voice-builder | `focux_voice` | **Absorb** | Interview questions + analysis steps are directly reusable. Produces about-me.md + voice.md — matches our memory conventions. |
| 2 | newsletter-voice | `focux_voice` | Absorb | Newsletter-specific layer on top of voice. The hub of the hub-and-spoke. |
| 3 | profile-optimizer | `focux_account` | Adapt | LinkedIn-specific; generalize headline/about/featured strategy to any platform profile. |
| 4 | post-writer | `focux_content` | **Absorb** | Voice-aware drafting, always references voice files, code-block output. |
| 5 | graphic-designer | `focux_visual` | Adapt | Auto-selects HTML/CSS graphic vs AI infographic; platform-agnostic decision logic. |
| 6 | post-formatter | `focux_content` | **Absorb** | PAS/AIDA/BAB/STAR/SLAY framework definitions are directly reusable. |
| 7 | hook-generator | `focux_content` | **Absorb** | 6 two-line hooks, 40-char formula with digits/metrics. Deterministic structure. |
| 8 | content-matrix | `focux_content` | **Absorb** | Pillars x 8 formats (Actionable/Motivational/Analytical/Contrarian/Observation/X-vs-Y/Present-vs-Future/Listicle) = 32+ ideas. Exact format definitions captured. |
| 9 | post-scorer | `focux_analysis` | **Absorb** | Deterministic formula + top/bottom decile analysis + /50 scorecard. This IS our MEDIR measurement loop. |
| 10 | analytics-dashboard | `focux_analysis` | **Absorb** | xlsx → React/Recharts dashboard spec + 5 data-backed recommendations. Exact panel spec captured (engagement trend, follower growth, 4-quadrant scatter, day-of-week heatmap, demographics). |
| 11 | niche-research | `focux_research` | Adapt | Charlie uses Claude-for-Chrome browser scrolling; FOCUX uses model-native web search (Qwen Token Plan has built-in search) + last-30-days research patterns. Same goal: 20 verified stories, last 7 days. |
| 12 | gemini-infographic | `focux_visual` | Adapt | Whiteboard-style prompt recipe (480k impressions / 3 posts). Provider-neutral prompt output. |
| 13 | gemini-carousel | `focux_visual` | **Absorb** | Approval-gated brief → per-slide prompts. 1080x1350, max 15 words/slide, brand-kit.md. A perfect model for our gated generation. |
| 14 | quote-post | `focux_visual` | Adapt | Two-step: quote + Gemini image recreation prompt. |
| 15 | pinned-comment | `focux_content` | Adapt | Meme-style pin + matching image prompt. Community layer. |
| 16 | reels-scripting | `focux_video` | Adapt | Apify scrape + Gemini 2.5 Flash analysis → newsletter-aligned script. Generalize beyond Instagram. |
| 17 | youtube-thumbnail | `focux_visual` | Adapt | Thumbnail-first workflow, brand colours, high-CTR principles. |

## 5. What must change for FOCUX (do not copy verbatim)

1. **Personal voice leaking into skills.** Charlie hardcodes *"British English
   throughout"* and *"Never use em dashes"* in nearly every skill. That is *his* absence
   signal, not a universal rule. FOCUX keeps these in the voice profile (absence
   signals), never in the skill.
2. **Claude-specific tooling.** `AskUserQuestion` and Claude-for-Chrome are
   Claude-Code-specific. FOCUX is provider-neutral: interactive input via the shell's
   approval/ask surface, research via model-native web search.
3. **LinkedIn-only.** Skills target LinkedIn posts/profiles/analytics. FOCUX
   generalizes the same recipes to X, Instagram, YouTube, TikTok, Substack.
4. **Costly data steps are ungated.** Apify scrapes cost ~$0.50 each. In FOCUX,
   data procurement is a `CONTENT`-class money-gate action: REVIEW before spend, with
   idempotency keys and cached data reuse (Charlie already caches `*-all-posts.json`).
5. **Fallback benchmarks must stay labeled.** Borrowing Charlie's benchmarks is fine
   when clearly named as external data; FOCUX must never present borrowed benchmarks as
   the user's own.

## 6. What this validates about our layer

- Our `SKILL.md` format + `tools/skill_validator.py` matches a 3k-star production
  system (`validate-skills.sh`). The format is industry-standard.
- Shared-context markdown files read by every skill = our memory conventions
  (`about-me.md`/`voice.md` ≈ our `memory/` profiles).
- Approval gates before generation = our money-gate philosophy applied to content, not
  just money.
- Skills as portable markdown with trigger phrases = exactly our 13-skill layer model.

## 7. Absorption plan into THE FOCUX

- **P0:** `focux_voice` (voice-builder interview + analysis absorbed; absence-signal
  profile) + `focux_content` ideation (content-matrix, hook-generator).
- **P1:** `focux_content` drafting (post-writer + post-formatter frameworks) with
  money-gate on publish; `focux_research` (niche-research adapted to model-native search).
- **P2:** `focux_analysis` (post-scorer formula + analytics-dashboard spec) — closes the
  MEDIR loop: MEDIR uses REAL data, not vibes.
- **P3:** `focux_visual` (carousel with approval gate, infographic, quote-post,
  thumbnail) + `focux_video` (reels-scripting generalized).
- **P4:** `focux_account` (profile-optimizer generalized) + platform adapters.

Reference material retained at `references/social-media-skills/` (MIT license file
included) so future skill work can lift exact recipes (interview JSON, format
definitions, prompt templates, dashboard panel spec).
