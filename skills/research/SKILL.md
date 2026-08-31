---
name: research
description: Market and product research with verified sources; every claim keeps a source URL and an evidence note.
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - curl
    emoji: "🔍"
---

# Research

Gather market, competitor, pricing and product information. Research is
READ-ONLY: it never changes business state and never triggers the money gate,
but its outputs feed decisions and the content plan.

## Process

1. Define the question and the decision it will inform.
2. Search the live web; prefer primary sources (vendor docs, official APIs,
   release notes) over aggregators.
3. For every factual claim, record: claim, source URL, date retrieved,
   evidence note (exact quote or data point).
4. Write findings as a draft in `memory/workspace/<role>/` (see business-memory
   for the decision record format) and present a summary to the user with
   sources.

## Rules

- Never invent a source. If you did not retrieve it, do not cite it.
- Distinguish shipped features from roadmaps/promises.
- Note data residency and pricing in the local currency of the vendor.
- When comparing tools (e.g. ecommerce platforms, model providers), give the
  decision criteria first, then the evidence per option.
