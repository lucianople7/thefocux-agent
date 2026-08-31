---
name: idle-review
description: Post-session consolidation — distill lessons from the finished work into durable memory, isolated, with backups and write-protected built-ins.
version: 1.0.0
metadata:
  openclaw:
    emoji: "💤"
---

# Idle Review

After work reaches `verified`, or at a scheduled quiet time, consolidate the
session: distill lessons into durable memory, propose skill improvements, and
hand unfinished tasks to the next session. The review is isolated, backs up
before every write, and never touches built-ins.

## When

- After a work item reaches `verified` (per the workflow-stages skill).
- At a scheduled quiet time (per the cadence skill).

## Rules

1. **Isolation**: the review runs in a separate context restricted to the
   memory and skills toolsets. It cannot execute actions, move money, or
   touch the shell.
2. **Outputs**:
   a. Consolidated lessons → append to `memory/MEMORY.md` in a dated section,
      per the business-memory skill.
   b. Skill-description improvements → propose to the self-improvement skill
      (evidence-gated).
   c. Unfinished tasks → note in `memory/work/` ROADMAP for the next session.
3. **Consolidation discipline**: merge duplicates; prune entries beyond a
   bounded size (~50 core entries); never delete history — supersede, not
   delete; take backups before any write; built-in skills and memory files
   are write-protected.

## Never

- Never run an idle review with shell, web, or money access.
- Never write a lesson from a single anecdote without evidence.
- Never let the review delete or rewrite immutable base content.
- Never auto-publish any review output.
