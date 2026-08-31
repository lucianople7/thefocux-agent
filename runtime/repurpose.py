"""FOCUX Content Multiplier — 1 asset in, 20+ distributable assets out.

The revenue multiplier: one piece of core content (a newsletter issue, a
video, a research note) is repurposed into 20+ structured outputs, each
tuned to a platform, each with a hook and a CTA pointing at the offer
ladder. This is the mechanism behind the "20x" — one unit of creative work
becomes twenty units of reach, and reach converts through the offer.

The multiplier is deterministic in STRUCTURE (which outputs, what each needs,
anti-spam gate); the LLM fills each output's text. Every output passes Law II
(no spam/extraction) before it is proposed — a multiplier never multiplies
noise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from policy.constitution import check_law2

#: The 20 output blueprints. Each = platform, format, what to write, CTA style.
OUTPUT_BLUEPRINTS: tuple[dict[str, str], ...] = (
    {"id": "linkedin-post", "platform": "LinkedIn", "format": "post",
     "brief": "1 concise post (180-250 words) teaching the core insight",
     "cta": "mention the lead magnet"},
    {"id": "x-thread", "platform": "X", "format": "thread (5-8 tweets)",
     "brief": "tease + numbered insights + proof + CTA",
     "cta": "link to the full asset"},
    {"id": "x-post", "platform": "X", "format": "single post",
     "brief": "one sharp insight with a number or contrarian claim",
     "cta": "reply-gate or link"},
    {"id": "instagram-carousel", "platform": "Instagram", "format": "carousel outline (8 slides)",
     "brief": "cover hook, 6 body slides one idea each, CTA slide",
     "cta": "save + DM for the freebie"},
    {"id": "instagram-reel", "platform": "Instagram", "format": "reel script (30-45s)",
     "brief": "hook 3s, value 20s, CTA 7s",
     "cta": "follow + link in bio"},
    {"id": "youtube-script", "platform": "YouTube", "format": "short script (60-90s)",
     "brief": "hook, 3 points, CTA",
     "cta": "subscribe + comment"},
    {"id": "youtube-thumbnail", "platform": "YouTube", "format": "thumbnail prompt",
     "brief": "high-CTR visual prompt from the insight",
     "cta": "n/a"},
    {"id": "newsletter-blurb", "platform": "Newsletter", "format": "section for the next issue",
     "brief": "expand the insight into a newsletter section",
     "cta": "reply with question / subscribe"},
    {"id": "email-tip", "platform": "Email", "format": "short tip (120 words)",
     "brief": "one actionable tip + soft offer",
     "cta": "link to the offer"},
    {"id": "quote-post", "platform": "LinkedIn", "format": "quote + caption",
     "brief": "a quotable line from the insight + caption",
     "cta": "tag someone"},
    {"id": "pinned-comment", "platform": "LinkedIn", "format": "pinned comment + image prompt",
     "brief": "meme-style pin that drives engagement",
     "cta": "comment 'yes' for the guide"},
    {"id": "podcast-bullet", "platform": "Podcast", "format": "monologue bullet (90s)",
     "brief": "speakable version of the insight",
     "cta": "visit the site"},
    {"id": "community-post", "platform": "Reddit/community", "format": "genuine question + insight",
     "brief": "value-first post for a niche community",
     "cta": "no self-promo; engage"},
    {"id": "blog-section", "platform": "Blog", "format": "section for a post",
     "brief": "long-form expansion of the insight",
     "cta": "newsletter signup"},
    {"id": "case-study-snippet", "platform": "Website", "format": "proof snippet",
     "brief": "the insight framed as a mini case study",
     "cta": "book a call"},
    {"id": "faq-answer", "platform": "Website", "format": "FAQ answer",
     "brief": "the insight as a customer-question answer",
     "cta": "link to product"},
    {"id": "slide-deck", "platform": "Slides", "format": "10-slide deck outline",
     "brief": "title, 8 content slides, CTA",
     "cta": "final slide offer"},
    {"id": "tiktok-script", "platform": "TikTok", "format": "script (20-30s)",
     "brief": "fast hook, one point, CTA",
     "cta": "follow for part 2"},
    {"id": "meme-idea", "platform": "X", "format": "meme concept",
     "brief": "visual joke based on the insight",
     "cta": "n/a"},
    {"id": "seo-summary", "platform": "Web/SEO", "format": "50-word summary",
     "brief": "meta description / schema-ready summary",
     "cta": "n/a"},
)


@dataclass(frozen=True)
class MultipliedAsset:
    id: str
    platform: str
    format: str
    brief: str
    cta: str
    draft: str = ""  # LLM fills this; structure is deterministic
    passed_gate: bool = True

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "platform": self.platform,
            "format": self.format,
            "brief": self.brief,
            "cta": self.cta,
            "draft": self.draft,
        }


def multiplier_plan(asset_type: str = "newsletter") -> list[MultipliedAsset]:
    """The 20x plan for one core asset (deterministic structure)."""
    return [
        MultipliedAsset(
            id=bp["id"], platform=bp["platform"], format=bp["format"],
            brief=bp["brief"], cta=bp["cta"],
        )
        for bp in OUTPUT_BLUEPRINTS
    ]


def write_asset(
    asset: MultipliedAsset,
    core_insight: str,
    *,
    offer: str = "",
    write: object | None = None,
) -> MultipliedAsset:
    """Fill one asset: Law-II gate first, then LLM draft (if provided).

    ``write`` is an optional callable ``(asset, core_insight, offer) -> str``
    (the LLM). Without it, the draft stays empty (structure only) — the gate
    still runs on the brief so a multiplier never multiplies spam.
    """
    # Law II: the asset must not contain extraction signals in its brief.
    verdict = check_law2(f"{asset.brief} {core_insight} {offer}")
    if not verdict.passed:
        return MultipliedAsset(
            id=asset.id, platform=asset.platform, format=asset.format,
            brief=asset.brief, cta=asset.cta, draft="",
            passed_gate=False,
        )
    draft = ""
    if write is not None:
        try:
            draft = str(write(asset, core_insight, offer))
        except Exception:  # noqa: BLE001 - draft is best-effort
            draft = ""
    return MultipliedAsset(
        id=asset.id, platform=asset.platform, format=asset.format,
        brief=asset.brief, cta=asset.cta, draft=draft, passed_gate=True,
    )


def multiply(
    core_insight: str,
    *,
    offer: str = "",
    write: object | None = None,
) -> list[MultipliedAsset]:
    """1 -> 20: the full multiplier pass over one core asset."""
    return [write_asset(a, core_insight, offer=offer, write=write)
            for a in multiplier_plan()]


def format_plan(assets: list[MultipliedAsset]) -> str:
    lines = [f"CONTENT MULTIPLIER — {len(assets)} outputs from 1 asset"]
    for asset in assets:
        gate = "OK " if asset.passed_gate else "GATE"
        lines.append(
            f"  [{gate}] {asset.id:24s} {asset.platform:12s} {asset.format}"
        )
    lines.append(f"\n{sum(1 for a in assets if a.passed_gate)} passed the gate")
    return "\n".join(lines)
