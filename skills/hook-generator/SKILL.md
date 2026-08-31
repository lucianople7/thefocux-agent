---
name: hook-generator
description: >-
  Generate 6 two-line hook variations for any topic using the 40-char opening
  plus 40-char contrast formula. Frames: number-led, bold claim, contrarian,
  question, personal story, news. Trigger: "write me hooks", "hook ideas",
  "I need a hook for a post about...".
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python
    emoji: "🪝"
---

# Hook Generator

Six two-line hooks per topic: a 40-char opening line + a 40-char contrast
line, across the six frames that perform best (number-led 31%, bold claim 27%,
contrarian 18% per Charlie Hills benchmark data). Structure owned by
`policy/focux_content.py` (deterministic); the agent rewrites each hook in the
user's voice before publishing.

## When to use

- User says: "write me hooks", "hook ideas", "generate hooks", "I need a hook
  for a post about X", or pastes a topic asking for openers.
- Drafting flow: hooks before the body, always in the user's voice.

## Steps

### 1. Get the topic

If not provided, ask for it in one line.

### 2. Generate

```python
from policy.focux_content import generate_hooks, render_hooks
hooks = generate_hooks(topic)
print(render_hooks(hooks))
```

### 3. Voice-adapt

Rewrite each hook in the user's voice using `voice.md` (rhythm, tone,
absence signals). Keep the frame structure and the 40/40 two-line shape.

### 4. Output

Show all six, framed by their style names, so the user can pick one to draft
from.

## Rules

- Fast output, no preamble.
- Hooks must be specific (digits, names, metrics) — never generic.
- Respect the voice profile's absence signals (e.g. no rhetorical questions
  if the voice never uses them).
