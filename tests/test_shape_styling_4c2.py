"""
tests/test_shape_styling_4c2.py
================================

Step 4c.2 — Shape visual styling round-trip tests.

Coverage:
  - fill_color (solid)
  - stroke_color, stroke_width, stroke_pattern
  - shadow (enabled, color, offset, angle, opacity, radius)
  - opacity
  - reflection

Pattern: load SVEF → mutate one property on a TextBlock's shape style →
save → reopen → assert.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa.color import Color


REPO = Path(__file__).resolve().parent.parent


def _find_target_text(deck, needle: str = "Years of Experience"):
    for slide in deck.slide:
        for tb in slide.texts:
            if needle in tb.text:
                return tb
    return None


def test_read_shape_visuals_from_real_deck():
    """Smoke: read fill/stroke/shadow/opacity from a real text block."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    assert tb is not None
    v = tb.visual_summary()
    assert isinstance(v, dict)
    # SVEF text blocks resolve to a chain that has at least stroke + opacity
    assert tb.opacity is not None
    assert tb.stroke_color is not None
    assert tb.stroke_width is not None
    print(
        f"\n  Read OK: opacity={tb.opacity} stroke_color={tb.stroke_color.as_hex()} "
        f"stroke_width={tb.stroke_width} pattern={tb.stroke_pattern}"
    )
    deck.close()


def test_fill_color_round_trip(tmp_path):
    """4c.2: set_fill_color persists."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    target = Color.from_hex("#F37100")  # Brainworks orange
    assert tb.set_fill_color(target), "set_fill_color returned False"
    out = tmp_path / "fill.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    got = tb2.fill_color
    print(f"\n  fill_color: target={target.as_hex()} got={got.as_hex() if got else None}")
    assert got is not None
    assert abs(got.r - target.r) < 1e-3
    assert abs(got.g - target.g) < 1e-3
    assert abs(got.b - target.b) < 1e-3
    deck2.close()


def test_stroke_color_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    target = Color.from_hex("#003366")
    assert tb.set_stroke_color(target)
    out = tmp_path / "stroke_color.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    got = tb2.stroke_color
    print(f"\n  stroke_color: target={target.as_hex()} got={got.as_hex() if got else None}")
    assert got is not None
    assert abs(got.r - target.r) < 1e-3
    deck2.close()


def test_stroke_width_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    orig = tb.stroke_width
    assert tb.set_stroke_width(3.5)
    out = tmp_path / "stroke_width.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    print(f"\n  stroke_width: {orig} -> {tb2.stroke_width}")
    assert abs(tb2.stroke_width - 3.5) < 1e-3
    deck2.close()


def test_stroke_pattern_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    orig = tb.stroke_pattern
    assert tb.set_stroke_pattern("solid")
    out = tmp_path / "stroke_pattern.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    print(f"\n  stroke_pattern: {orig} -> {tb2.stroke_pattern}")
    assert tb2.stroke_pattern == "solid"
    deck2.close()


def test_shadow_round_trip(tmp_path):
    """4c.2: shadow with multiple params persists."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    assert tb.set_shadow(
        enabled=True,
        color="#FF0000",
        offset=8.0,
        angle=270.0,
        opacity=0.75,
        radius=6,
    )
    out = tmp_path / "shadow.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    sh = tb2.shadow
    print(f"\n  shadow: {sh}")
    assert sh is not None
    assert sh["isEnabled"] is True
    assert abs(sh["offset"] - 8.0) < 1e-3
    assert abs(sh["angle"] - 270.0) < 1e-3
    assert abs(sh["opacity"] - 0.75) < 1e-3
    # color check
    c = Color.from_dict(sh["color"])
    assert abs(c.r - 1.0) < 1e-3 and c.g < 1e-3 and c.b < 1e-3
    deck2.close()


def test_opacity_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    orig = tb.opacity
    assert tb.set_opacity(0.6)
    out = tmp_path / "opacity.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    print(f"\n  opacity: {orig} -> {tb2.opacity}")
    assert abs(tb2.opacity - 0.6) < 1e-3
    deck2.close()


def test_reflection_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    orig = tb.reflection_enabled
    assert tb.set_reflection(opacity=0.4)
    out = tmp_path / "reflection.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    print(f"\n  reflection_enabled: {orig} -> {tb2.reflection_enabled}")
    assert tb2.reflection_enabled is True
    deck2.close()


def test_clear_stroke_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = _find_target_text(deck)
    assert tb.clear_stroke()
    out = tmp_path / "no_stroke.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = _find_target_text(deck2)
    p = tb2.stroke_pattern
    print(f"\n  stroke_pattern after clear: {p}")
    assert p in ("none", "empty"), f"Expected none/empty, got {p!r}"
    deck2.close()
