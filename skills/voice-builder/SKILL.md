---
name: voice-builder
description: >-
  Build a personalised voice profile (about-me.md + voice.md with absence signals)
  from a short interview plus 3 to 5 writing samples. Every content skill reads
  these files before drafting. Use at the start of any project: "build my voice",
  "learn my voice", "set up my content system", "train on my writing".
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python
    emoji: "🎙️"
---

# Voice Builder

Builds the FOCUX voice foundation: `about-me.md` (who you are, audience,
pillars, point of view, brand promise, off-limits) and `voice.md` (how the
voice writes AND what it never does — the absence signals). The structure and
analysis are owned by `policy/focux_voice.py` (deterministic, testable); the
interview and qualitative analysis are the agent's job on top of it.

## When to use

- User says: "build my voice", "learn my voice", "train on my writing",
  "set up my content system", or drops writing samples at project start.
- First-time FOCUX setup before any content skill runs.

## Steps

### 1. Run the interview (two batches)

Ask `INTERVIEW_BATCH_1` (About you, Audience, Topics, Hot take), then
`INTERVIEW_BATCH_2` (Brand promise, Off limits) from `policy/focux_voice.py`.
Use the shell's interactive/approval surface for input; never type options as
plain chat text.

### 2. Collect 3 to 5 samples

Ask for published writing (posts, newsletter issues, essays, emails). Minimum
3 samples before analysis. If none available, proceed with the interview only
and mark the voice profile as sample-free.

### 3. Analyse and write the profile

- Run `analyze_samples(samples)` for the deterministic signals (sentence
  length, em-dash/hashtag/question presence).
- Analyse voice signals across ALL samples (tone, rhythm, hooks, openings,
  closings, signature phrases) and ABSENCE signals (what 0-of-N samples never
  do).
- Render `about-me.md` and `voice.md` with `render_about_me` / `render_voice`,
  saving both into the project root (or `memory/` in the layer).
- Absence signals come from observation, never from a generic banned list.

### 4. Confirm and hand off

Tell the user both files are ready and every future draft will reference them.
Offer: "write a post", "build my newsletter voice", "score a draft".

## Rules

- Go straight to the interview; no summary, no preamble.
- Never invent patterns not in the samples; note contradictions.
- Absence signals only from observed gaps (0 of N).
- Keep about-me.md under 300 words, voice.md under 500 words.
- The voice profile is loaded by every content skill before drafting.
