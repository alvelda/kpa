"""
tests/test_styling_4c1.py
==========================

Step 4c.1 — Text styling round-trip tests.

Coverage matrix (`docs/COVERAGE.md`):
  - font_name, font_size, bold, italic, underline, color (charProperties)
  - alignment, line_spacing, first_line_indent, space_before, space_after
    (paraProperties)

Pattern: load SVEF → mutate one property → save → reopen → assert.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa.color import Color


REPO = Path(__file__).resolve().parent.parent


def _find_target_text(deck, needle: str = "Years of Experience"):
    """Return (slide_id, text_block) for the first slide whose text
    contains ``needle``."""
    for slide in deck.slide:
        for tb in slide.texts:
            if needle in tb.text:
                return slide.slide_id, tb
    return None, None


def test_read_styles_from_real_deck():
    """Smoke: read-only — confirm we get sensible style values from SVEF."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    assert tb is not None, "Couldn't find target text in SVEF"
    assert tb.font_name is not None
    assert tb.font_size is not None and tb.font_size > 0
    assert isinstance(tb.bold, bool)
    assert tb.color is not None
    assert isinstance(tb.color, Color)
    print(
        f"\n  Read OK: font={tb.font_name!r} size={tb.font_size} "
        f"bold={tb.bold} color={tb.color.as_hex()} align={tb.alignment_name}"
    )
    deck.close()


def test_font_name_round_trip(tmp_path):
    """4c.1: set_font_name persists through save+reload."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    assert tb is not None
    orig_font = tb.font_name
    assert tb.set_font_name("Georgia"), "set_font_name returned False"
    out = tmp_path / "font.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    assert tb2 is not None
    print(f"\n  font_name: {orig_font!r} -> {tb2.font_name!r}")
    assert tb2.font_name == "Georgia"
    deck2.close()


def test_font_size_round_trip(tmp_path):
    """4c.1: set_font_size persists."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    orig_size = tb.font_size
    assert tb.set_font_size(42.0)
    out = tmp_path / "size.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    print(f"\n  font_size: {orig_size} -> {tb2.font_size}")
    assert abs(tb2.font_size - 42.0) < 0.01
    deck2.close()


def test_bold_italic_underline_round_trip(tmp_path):
    """4c.1: bold/italic/underline persist."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    tb.set_bold(False)
    tb.set_italic(True)
    tb.set_underline(False)
    out = tmp_path / "bif.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    print(f"\n  bold/italic/underline: {tb2.bold}/{tb2.italic}/{tb2.underline}")
    assert tb2.bold is False
    assert tb2.italic is True
    assert tb2.underline is False
    deck2.close()


def test_color_round_trip(tmp_path):
    """4c.1: color persists with the exact RGBA values."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    target = Color.from_hex("#F37100")  # Brainworks orange
    tb.set_color(target)
    out = tmp_path / "color.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    got = tb2.color
    print(f"\n  color: target={target.as_hex()} got={got.as_hex()}")
    assert got is not None
    assert abs(got.r - target.r) < 1e-3
    assert abs(got.g - target.g) < 1e-3
    assert abs(got.b - target.b) < 1e-3
    deck2.close()


def test_alignment_round_trip(tmp_path):
    """4c.1: alignment persists across save/reload."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    orig = tb.alignment_name
    tb.set_alignment("center")
    out = tmp_path / "align.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    print(f"\n  alignment: {orig} -> {tb2.alignment_name}")
    assert tb2.alignment_name == "center"
    assert tb2.alignment == 2
    deck2.close()


def test_line_spacing_round_trip(tmp_path):
    """4c.1: line_spacing persists."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    orig = tb.line_spacing
    tb.set_line_spacing(1.5)
    out = tmp_path / "linesp.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    print(f"\n  line_spacing: {orig} -> {tb2.line_spacing}")
    assert abs(tb2.line_spacing - 1.5) < 1e-3
    deck2.close()


def test_paragraph_spacing_round_trip(tmp_path):
    """4c.1: space_before and space_after persist."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sid, tb = _find_target_text(deck)
    tb.set_space_before(12.0)
    tb.set_space_after(8.0)
    out = tmp_path / "parasp.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    sid2, tb2 = _find_target_text(deck2)
    print(f"\n  space_before={tb2.space_before} space_after={tb2.space_after}")
    assert abs(tb2.space_before - 12.0) < 1e-3
    assert abs(tb2.space_after - 8.0) < 1e-3
    deck2.close()


def test_color_value_type_smoke():
    """Color constructors all produce equivalent values."""
    a = Color.from_hex("#F37100")
    b = Color.from_rgb255(243, 113, 0)
    c = Color(243 / 255.0, 113 / 255.0, 0.0)
    assert abs(a.r - b.r) < 1e-3
    assert abs(a.g - b.g) < 1e-3
    assert abs(a.b - b.b) < 1e-3
    assert a.as_hex() == "#F37100"
    d = Color.from_dict(a.as_dict())
    assert d.as_hex() == a.as_hex()
