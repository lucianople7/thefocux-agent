"""Tests for policy/focux_voice.py — voice profile builder."""
from __future__ import annotations

import pytest

from policy.focux_voice import (
    INTERVIEW_BATCH_1,
    INTERVIEW_BATCH_2,
    INTERVIEW_BATCHES,
    VoiceProfile,
    absence_signals,
    analyze_samples,
    build_profile,
    render_about_me,
    render_voice,
)


def test_interview_structure() -> None:
    assert len(INTERVIEW_BATCHES) == 2
    assert len(INTERVIEW_BATCH_1) == 4
    assert len(INTERVIEW_BATCH_2) == 2
    for batch in INTERVIEW_BATCHES:
        for q in batch:
            assert q.header
            assert q.question
            assert len(q.question) > 10


def test_analyze_samples_empty() -> None:
    stats = analyze_samples(())
    assert stats.count == 0
    assert stats.avg_sentence_length == 0.0


def test_analyze_samples_detects_absence() -> None:
    samples = (
        "Short sentences only. No dashes here. No hashtags here either.",
        "Another clean sample. Still no dashes. Still no questions asked.",
        "Third sample. No em dash. No hash. Just periods.",
    )
    stats = analyze_samples(samples)
    assert stats.count == 3
    assert not stats.uses_em_dash
    assert not stats.uses_hashtags
    signals = absence_signals(stats)
    assert any("em dashes" in s for s in signals)
    assert any("hashtags" in s for s in signals)


def test_analyze_samples_detects_presence() -> None:
    samples = ("This one has a dash — see? #tag and a question?",)
    stats = analyze_samples(samples)
    assert stats.uses_em_dash
    assert stats.uses_hashtags
    assert stats.uses_questions
    assert absence_signals(stats) == []  # nothing absent


def test_render_about_me() -> None:
    profile = VoiceProfile(
        name_role="Luciano, founder",
        audience="Founders who want an AI business agent",
        topic_pillars=["AI agents", "Content systems"],
        point_of_view="Most agents are toys",
        brand_promise="Practical",
        off_limits=["Politics"],
    )
    md = render_about_me(profile)
    assert "# About Me" in md
    assert "Luciano, founder" in md
    assert "- AI agents" in md
    assert "Practical" in md
    assert "Politics" in md


def test_render_voice_includes_absence() -> None:
    profile = VoiceProfile(
        who_i_sound_like="Blunt and practical",
        tone=["direct"],
        tone_never=["corporate"],
        sentence_rhythm="Short sentences",
        hook_patterns=["Number-led"],
        hook_never=["Question hooks"],
        how_i_open="With a claim",
        how_i_close="With an ask",
        signature_phrases=["ship it"],
        off_limits_writing=["no em dashes"],
        never_does=["Never pitch in the first line"],
    )
    md = render_voice(profile)
    assert "## Off-limits (absence signals)" in md
    assert "no em dashes" in md
    assert "Never pitch in the first line" in md


def test_build_profile_merges_absence_signals() -> None:
    samples = (
        "Clean sample one. No dash. No hash.",
        "Clean sample two. No dash. No hash.",
        "Clean sample three. No dash. No hash.",
    )

    def analysis(answers, stats):
        return VoiceProfile(
            who_i_sound_like="Tester",
            tone=["clean"],
            tone_never=[],
            sentence_rhythm="short",
            hook_patterns=[],
            hook_never=[],
            how_i_open="",
            how_i_close="",
            signature_phrases=[],
            off_limits_writing=[],
            never_does=[],
        )

    profile = build_profile({}, samples=samples, analysis=analysis)
    assert any("em dashes" in s for s in profile.off_limits_writing)
    assert any("hashtags" in s for s in profile.off_limits_writing)


def test_build_profile_without_samples_keeps_analysis() -> None:
    def analysis(answers, stats):
        assert stats is None
        return VoiceProfile(who_i_sound_like="Only interview, no samples")

    profile = build_profile({}, samples=(), analysis=analysis)
    assert profile.who_i_sound_like == "Only interview, no samples"
    assert profile.off_limits_writing == []
