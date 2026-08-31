---
name: content-pipeline
description: Weekly content engine — plan themes, generate assets (image/video), assemble, schedule via a publishing tool with a mandatory draft review gate before anything is visible.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🎬"
---

# Content Pipeline

Turn the weekly content plan (from the cadence skill) into published content.

## Stages

1. **Plan** — from the weekly plan, pick themes, hooks and formats. Respect
   platform limits (e.g. YouTube daily upload quota, TikTok per-account caps).
2. **Generate** — create assets with the configured generators (Qwen-Image for
   images, Wan for video, Remotion for deterministic assembly). Record the
   model, prompt and cost per asset in the draft.
3. **Draft** — assemble the post: hook, body, asset, call to action, channel.
   Save every draft with status `draft`.
4. **Review gate** — publishing is a CONTENT-class action: route through the
   money-gate skill. Nothing becomes visible without approval, period.
   Approved drafts move to `scheduled`.
5. **Publish** — hand scheduled posts to the publishing tool (Postiz MCP or
   equivalent). After each publish, write a receipt with the post id and URL
   and the approval fingerprint from the money-gate.

## Never

- Never publish to a live channel without the review gate.
- Never auto-retry a failed publish without a fresh approval.
- Never claim a post was published from memory — verify with the publishing
  tool and record the URL in the receipt.
