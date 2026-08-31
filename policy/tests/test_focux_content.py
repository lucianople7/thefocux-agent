"""Tests for policy/focux_content.py — content matrix + hook generator."""
from __future__ import annotations

import pytest

from policy.focux_content import (
    CONTENT_FORMATS,
    ContentMatrix,
    FORMAT_DEFINITIONS,
    HOOK_FRAMES,
    generate_hooks,
    render_hooks,
)


def test_matrix_requires_3_to_5_pillars() -> None:
    with pytest.raises(ValueError):
        ContentMatrix(("one", "two"))
    with pytest.raises(ValueError):
        ContentMatrix(("a", "b", "c", "d", "e", "f"))
    matrix = ContentMatrix(("AI", "Marketing", "Leadership"))
    assert matrix.dimensions() == (3, 8)


def test_matrix_formats_are_eight_in_order() -> None:
    assert len(CONTENT_FORMATS) == 8
    assert CONTENT_FORMATS[0] == "Actionable"
    assert CONTENT_FORMATS[-1] == "Listicle"
    assert len(FORMAT_DEFINITIONS) == 8


def test_matrix_fill_generates_32_plus() -> None:
    matrix = ContentMatrix(("AI", "Marketing", "Leadership", "Sales"))
    cells = matrix.fill(lambda pillar, fmt: f"{pillar} x {fmt} headline")
    assert len(cells) == 4 * 8 == 32
    assert len({c.pillar for c in cells}) == 4
    assert len({c.format_name for c in cells}) == 8


def test_matrix_fill_rejects_blank() -> None:
    matrix = ContentMatrix(("AI", "Marketing", "Leadership"))
    with pytest.raises(ValueError):
        matrix.fill(lambda pillar, fmt: "")


def test_matrix_fill_rejects_duplicate_per_pillar() -> None:
    matrix = ContentMatrix(("AI", "Marketing", "Leadership"))

    def dup(pillar, fmt):
        return "same idea"

    with pytest.raises(ValueError):
        matrix.fill(dup)


def test_matrix_render_markdown() -> None:
    matrix = ContentMatrix(("AI", "Marketing", "Leadership"))
    cells = matrix.fill(lambda p, f: f"{p}: {f}")
    md = matrix.render_markdown(cells)
    assert md.startswith("| Pillar |")
    assert "| Actionable |" in md
    assert "AI" in md
    assert "```" not in md  # no code fence


def test_hook_generation_six_frames() -> None:
    hooks = generate_hooks("personal branding")
    assert len(hooks) == 6
    assert [h.frame for h in hooks] == list(HOOK_FRAMES)
    for hook in hooks:
        assert hook.opening
        assert hook.contrast
        assert "\n" in hook.two_line


def test_hook_generation_blank_topic_raises() -> None:
    with pytest.raises(ValueError):
        generate_hooks("   ")


def test_hook_number_parameter() -> None:
    hooks = generate_hooks("email marketing", number=3)
    assert len(hooks) == 3


def test_hook_render() -> None:
    hooks = generate_hooks("newsletters")
    rendered = render_hooks(hooks)
    assert "[number-led]" in rendered
    assert "newsletters" in rendered


def test_hook_contains_digits_for_number_led() -> None:
    hooks = generate_hooks("newsletters")
    number_led = next(h for h in hooks if h.frame == "number-led")
    assert "3-step" in number_led.opening
