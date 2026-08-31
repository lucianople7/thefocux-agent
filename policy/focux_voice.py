"""FOCUX Voice — deterministic voice-profile builder.

Pattern absorbed from Charlie Hills' voice-builder skill (MIT): a voice
foundation (about-me + voice profile with ABSENCE signals) that every content
skill reads before drafting. The LLM does the interview and the pattern
analysis; this module owns the STRUCTURE — the interview questions, the
profile schema, the absence-signal extraction, and the markdown writers — so
the profile is consistent, testable, and shell-agnostic.

Absence signals are the negative knowledge base: what the voice NEVER does,
drawn from 0-of-N sample observations, never from a generic banned list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


# --- Interview ----------------------------------------------------------------

@dataclass(frozen=True)
class InterviewQuestion:
    header: str
    question: str
    multi_select: bool = False
    options: tuple[tuple[str, str], ...] = ()  # (label, description)


#: Batch 1 — identity, audience, topics, point of view.
INTERVIEW_BATCH_1: tuple[InterviewQuestion, ...] = (
    InterviewQuestion(
        "About you",
        "What is your name and what do you do?",
        options=(
            ("Founder", "I run my own company or consultancy"),
            ("Marketing lead", "I lead marketing at a company"),
            ("Creator", "I create content as my main thing"),
            ("Sales leader", "I lead a sales team or run BD"),
        ),
    ),
    InterviewQuestion(
        "Audience",
        "Who are you writing for?",
        options=(
            ("Founders and CEOs", "Decision makers running companies"),
            ("Marketers", "Marketing professionals at any level"),
            ("Job seekers", "People looking for their next role"),
            ("Other professionals", "A different group entirely"),
        ),
    ),
    InterviewQuestion(
        "Topics",
        "What are the 3 to 5 topics you want to be known for?",
        multi_select=True,
        options=(
            ("AI and automation", "How AI tools change work"),
            ("Marketing", "Strategy, content, growth"),
            ("Leadership", "Management, hiring, culture"),
            ("Personal brand", "Building an audience and reputation"),
        ),
    ),
    InterviewQuestion(
        "Hot take",
        "What is your point of view on your industry?",
        options=(
            ("Most advice is wrong", "The consensus in your industry is broken"),
            ("People overcomplicate it", "The answer is simpler than people think"),
            ("A big shift is coming", "Something is about to change"),
        ),
    ),
)

#: Batch 2 — brand promise, off-limits topics.
INTERVIEW_BATCH_2: tuple[InterviewQuestion, ...] = (
    InterviewQuestion(
        "Brand promise",
        "What is the one thing you want people to think when they see your name?",
        options=(
            ("This person is practical", "They give me things I use immediately"),
            ("This person is honest", "They tell me what others will not"),
            ("This person is ahead", "They see what is coming before everyone else"),
        ),
    ),
    InterviewQuestion(
        "Off limits",
        "What is one thing you refuse to write about?",
        options=(
            ("Politics", "No political takes, ever"),
            ("Personal life", "Keep it professional only"),
            ("Competitors", "No naming or shaming other people or brands"),
        ),
    ),
)

INTERVIEW_BATCHES: tuple[tuple[InterviewQuestion, ...], ...] = (
    INTERVIEW_BATCH_1,
    INTERVIEW_BATCH_2,
)


# --- Profile schema -----------------------------------------------------------

@dataclass
class VoiceProfile:
    # about-me
    name_role: str = ""
    audience: str = ""
    topic_pillars: list[str] = field(default_factory=list)
    point_of_view: str = ""
    brand_promise: str = ""
    off_limits: list[str] = field(default_factory=list)
    # voice
    who_i_sound_like: str = ""
    tone: list[str] = field(default_factory=list)
    tone_never: list[str] = field(default_factory=list)
    sentence_rhythm: str = ""
    hook_patterns: list[str] = field(default_factory=list)
    hook_never: list[str] = field(default_factory=list)
    how_i_open: str = ""
    how_i_close: str = ""
    signature_phrases: list[str] = field(default_factory=list)
    off_limits_writing: list[str] = field(default_factory=list)
    never_does: list[str] = field(default_factory=list)


# --- Absence-signal extraction (deterministic) --------------------------------

@dataclass(frozen=True)
class SampleStats:
    count: int
    avg_sentence_length: float
    uses_em_dash: bool
    uses_hashtags: bool
    uses_questions: bool
    avg_words: float


def analyze_samples(samples: tuple[str, ...]) -> SampleStats:
    """Deterministic signal extraction from writing samples.

    This is the machine part of the analysis; the LLM adds the qualitative
    layer (tone, hooks, openings) on top of these hard numbers.
    """
    if not samples:
        return SampleStats(0, 0.0, False, False, False, 0.0)
    sentences = 0
    words = 0
    uses_em_dash = False
    uses_hashtags = False
    uses_questions = False
    for sample in samples:
        uses_em_dash = uses_em_dash or "\u2014" in sample or "--" in sample
        uses_hashtags = uses_hashtags or "#" in sample
        uses_questions = uses_questions or "?" in sample
        words += len(sample.split())
        sentences += max(1, sample.count(".") + sample.count("!") + sample.count("?"))
    return SampleStats(
        count=len(samples),
        avg_sentence_length=round(words / max(1, sentences), 1),
        uses_em_dash=uses_em_dash,
        uses_hashtags=uses_hashtags,
        uses_questions=uses_questions,
        avg_words=round(words / len(samples), 1),
    )


def absence_signals(stats: SampleStats) -> list[str]:
    """Signals the samples consistently avoid (0-of-N observations)."""
    signals: list[str] = []
    if not stats.uses_em_dash:
        signals.append("no em dashes (0 of N samples)")
    if not stats.uses_hashtags:
        signals.append("no hashtags (0 of N samples)")
    if not stats.uses_questions:
        signals.append("no rhetorical questions (0 of N samples)")
    if stats.count >= 3 and stats.avg_sentence_length < 12:
        signals.append("short, staccato rhythm (avg under 12 words/sentence)")
    return signals


# --- Markdown writers ---------------------------------------------------------

def render_about_me(profile: VoiceProfile) -> str:
    """about-me.md: who the user is, audience, pillars, POV, promise."""
    pillars = "\n".join(f"- {p}" for p in profile.topic_pillars)
    limits = "\n".join(f"- {o}" for o in profile.off_limits)
    return f"""# About Me

## Name and role
{profile.name_role}

## Audience
{profile.audience}

## Topic pillars
{pillars}

## Point of view
{profile.point_of_view}

## Brand promise
{profile.brand_promise}

## Off limits
{limits}
"""


def render_voice(profile: VoiceProfile, stats: SampleStats | None = None) -> str:
    """voice.md: integrated profile incl. absence signals (the negative KB)."""
    tone = ", ".join(profile.tone) or "-"
    tone_never = ", ".join(profile.tone_never) or "-"
    hooks = "\n".join(f"- {h}" for h in profile.hook_patterns)
    hook_never = "\n".join(f"- {h}" for h in profile.hook_never)
    phrases = "\n".join(f"- {p}" for p in profile.signature_phrases)
    limits = "\n".join(f"- {w}" for w in profile.off_limits_writing)
    never = "\n".join(f"- {n}" for n in profile.never_does)
    if stats is not None:
        stats_block = (
            f"\n## Measured signals\n"
            f"- Samples: {stats.count}\n"
            f"- Avg sentence length: {stats.avg_sentence_length}\n"
            f"- Avg words per sample: {stats.avg_words}\n"
        )
    else:
        stats_block = ""
    return f"""# Voice Profile

## Who I sound like
{profile.who_i_sound_like}

## Tone
{profile.tone} (hits); never: {profile.tone_never}

## Sentence rhythm
{profile.sentence_rhythm}

## Hook patterns
{hooks}
Absent: {hook_never}

## How I open
{profile.how_i_open}

## How I close
{profile.how_i_close}

## Signature phrases
{phrases}

## Off-limits (absence signals)
{limits}

## What this voice never does
{never}
{stats_block}"""


# --- Pipeline -----------------------------------------------------------------

def build_profile(
    answers: dict[str, list[str]],
    *,
    samples: tuple[str, ...] = (),
    analysis: Callable[[dict[str, list[str]], SampleStats | None], VoiceProfile],
) -> VoiceProfile:
    """Run the voice pipeline: answers -> (stats) -> analysis -> profile.

    ``answers`` maps question headers to chosen labels (multi_select lists).
    ``analysis`` is the LLM-backed qualitative step; it receives the raw
    answers and the deterministic stats and must return a VoiceProfile.
    """
    stats = analyze_samples(samples)
    profile = analysis(answers, stats if samples else None)
    if profile.off_limits_writing or not samples:
        return profile
    # Merge deterministic absence signals unless the analysis already set them.
    profile.off_limits_writing.extend(absence_signals(stats))
    return profile
