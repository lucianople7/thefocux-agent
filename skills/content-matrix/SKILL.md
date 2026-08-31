---
name: content-matrix
description: >-
  Generate 32+ post ideas in one table by pairing the user's 3-5 content pillars
  with 8 proven formats (Actionable, Motivational, Analytical, Contrarian,
  Observation, X vs Y, Present vs Future, Listicle). Justin Welsh style.
  Trigger: "give me post ideas", "content matrix", "what should I post",
  "map out my content".
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python
    emoji: "📊"
---

# Content Matrix

Ideation engine: pillars x 8 formats = 32+ specific post headlines in one
table. Structure owned by `policy/focux_content.py` (deterministic, testable);
the agent fills the cells with specific, concrete headlines.

## When to use

- User says: "give me post ideas", "content matrix", "what should I post
  about", "content ideation", "map out my content for the month".
- Weekly planning: ANALIZAR -> PLANIFICAR loop.

## Steps

### 1. Gather inputs

Read `about-me.md` (and `voice.md` if present). If missing, ask for 2+
paragraphs describing who the user is, what they do, and what they discuss.
Then take 3 to 5 content pillars (from voice.md, typed, or suggested).

### 2. Build the matrix

```python
from policy.focux_content import ContentMatrix
matrix = ContentMatrix(pillars=("Pillar1", "Pillar2", "Pillar3"))
cells = matrix.fill(headline_for=lambda pillar, fmt: "<specific headline>")
```

Every cell is a SPECIFIC headline, not a theme. Good: "The 3-line hook
formula I stole from David Ogilvy". Bad: "Hooks". Use the format definitions
in `FORMAT_DEFINITIONS` to shape each cell.

### 3. Output

- Save to `content-matrix-YYYY-MM-DD.md` in the project and print the table
  inline as plain markdown (no code fence).
- Add one sentence naming the single strongest idea and why.

### 4. Offer the next move

Ask which cell to write as a full post (e.g. "Hooks x Contrarian") and hand it
to the post drafting flow.

## Rules

- Minimum 3 pillars, maximum 5. More dilutes the matrix.
- Every idea specific to BOTH pillar and format; no reuse across pillars.
- Tune language to the voice profile when present.
