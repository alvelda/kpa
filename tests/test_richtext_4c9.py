"""
tests/test_richtext_4c9.py
============================

Step 4c.9 \u2014 TSWP rich-text decode + encode.

Validates :mod:`kpa.richtext` against SVEF text bodies:
  - decode_storage produces correct paragraph + run structure
  - inline char-style overrides preserved on round-trip
  - paragraph splitting on '\n' (not on U+2028 soft line break)
  - set_paragraphs() rewrites range tables consistently
  - dict-form Paragraph input also accepted

Test fixtures:
  - recon/svef.key  (slide 0: known "Dr. Phillip Alvelda \\u2028 Managing
    Partner" text box + a 7-paragraph mixed-style biography text box)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa import Paragraph, Run


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"


def _find_textblock(slide, shape_id):
    for tb in slide.texts:
        if tb._shape_id == shape_id:
            return tb
    return None


# ============= decode =============


def test_decode_single_paragraph_with_inline_run():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Slide 0, text box 807121: 'Dr. Phillip Alvelda \u2028Managing Partner'
        # That's a SINGLE paragraph (U+2028 is a soft break) with 2 runs.
        tb = _find_textblock(deck.slide[0], "807121")
        assert tb is not None
        paras = tb.paragraphs
        assert len(paras) == 1, f"expected 1 para, got {len(paras)}"
        p = paras[0]
        assert "Managing Partner" in p.text
        # Two runs: the leading text + the styled "Managing Partner".
        assert len(p.runs) == 2
        assert p.runs[0].text.endswith("\u2028")
        assert p.runs[1].text == "Managing Partner"
        # The second run carries the inline char-style override.
        assert p.runs[1].char_style_id == "15632874"
    finally:
        deck.close()


def test_decode_multi_paragraph_with_list_styles():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Slide 0, text box 807146: 8-paragraph biography with bullets
        tb = _find_textblock(deck.slide[0], "807146")
        assert tb is not None
        paras = tb.paragraphs
        # Original has 7 paragraphs visible + 1 trailing (text ends with newline).
        assert len(paras) >= 7
        # Each paragraph carries a list_style_id.
        assert any(p.list_style_id is not None for p in paras)
        # At least one paragraph has multiple runs (inline char overrides).
        assert any(len(p.runs) > 1 for p in paras)
    finally:
        deck.close()


def test_decode_preserves_para_style_ids():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807146")
        paras = tb.paragraphs
        # The first non-empty paragraph carries the known style id 1591.
        ids = [p.para_style_id for p in paras if p.para_style_id]
        assert "1591" in ids or 1591 in ids, f"got {ids[:5]}"
    finally:
        deck.close()


# ============= round-trip mutation =============


def test_replace_with_two_paragraphs_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        old = tb.paragraphs[0]
        new_paragraphs = [
            Paragraph(
                text="Line A",
                para_style_id=old.para_style_id,
                list_style_id=old.list_style_id,
            ),
            Paragraph(
                text="Line B with EMPHASIS at end",
                para_style_id=old.para_style_id,
                list_style_id=old.list_style_id,
                runs=[
                    Run(text="Line B with "),
                    Run(text="EMPHASIS", char_style_id="15632874"),
                    Run(text=" at end"),
                ],
            ),
        ]
        tb.set_paragraphs(new_paragraphs)
        out = deck.save(tmp_path / "rt_a.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        tb2 = _find_textblock(deck2.slide[0], "807121")
        paras = tb2.paragraphs
        assert len(paras) == 2
        assert paras[0].text == "Line A"
        assert paras[1].text == "Line B with EMPHASIS at end"
        # Para-style ref survived.
        assert paras[0].para_style_id == old.para_style_id
        assert paras[1].para_style_id == old.para_style_id
        # Inline run with EMPHASIS char-style is back.
        assert len(paras[1].runs) == 3
        emp = next(r for r in paras[1].runs if r.text == "EMPHASIS")
        assert emp.char_style_id == "15632874"
    finally:
        deck2.close()


def test_dict_form_paragraphs(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        tb.set_paragraphs([
            {"text": "First", "para_style_id": "774055"},
            {
                "text": "Second WORD here",
                "para_style_id": "774055",
                "runs": [
                    {"text": "Second "},
                    {"text": "WORD", "char_style_id": "15632874"},
                    {"text": " here"},
                ],
            },
        ])
        out = deck.save(tmp_path / "rt_dict.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        tb2 = _find_textblock(deck2.slide[0], "807121")
        paras = tb2.paragraphs
        assert len(paras) == 2
        assert paras[0].text == "First"
        assert paras[1].text == "Second WORD here"
        word_run = next(r for r in paras[1].runs if r.text == "WORD")
        assert word_run.char_style_id == "15632874"
    finally:
        deck2.close()


def test_run_text_concat_must_match_paragraph():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        with pytest.raises(ValueError, match="runs don't match"):
            tb.set_paragraphs([
                Paragraph(
                    text="Hello world",
                    runs=[
                        Run(text="Hello"),
                        Run(text="MISMATCH"),  # doesn't concat to "Hello world"
                    ],
                )
            ])
    finally:
        deck.close()


def test_set_paragraphs_preserves_styleSheet_ref(tmp_path):
    """The TSWP.StorageArchive's styleSheet ref must survive a rewrite \u2014
    otherwise Keynote can't resolve the style ids on reload."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        before_ss = tb._storage_archive.get("styleSheet")
        tb.set_paragraphs([Paragraph(text="x")])
        after_ss = tb._storage_archive.get("styleSheet")
        assert before_ss == after_ss
        out = deck.save(tmp_path / "rt_ss.key")
    finally:
        deck.close()

    # And it must survive a reload.
    deck2 = kpa.Deck.from_template(out)
    try:
        tb2 = _find_textblock(deck2.slide[0], "807121")
        assert tb2._storage_archive.get("styleSheet") == before_ss
    finally:
        deck2.close()


def test_multi_paragraph_text_join_with_newline(tmp_path):
    """Three paragraphs should produce a body text with exactly two
    \\n separators (one between each adjacent pair)."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        tb.set_paragraphs([
            Paragraph(text="alpha"),
            Paragraph(text="beta"),
            Paragraph(text="gamma"),
        ])
        full = tb._storage_archive["text"][0]
        assert full == "alpha\nbeta\ngamma"
        out = deck.save(tmp_path / "rt_multi.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        tb2 = _find_textblock(deck2.slide[0], "807121")
        paras = tb2.paragraphs
        assert [p.text for p in paras] == ["alpha", "beta", "gamma"]
    finally:
        deck2.close()


def test_decode_empty_storage():
    """An empty storage archive (no text) decodes as empty list."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Find a TSWP.StorageArchive with no text.
        for sidx in range(min(10, len(deck.slide))):
            s = deck.slide[sidx]
            for aid, arch in s._archive_index.items():
                for obj in arch.get("objects", []):
                    if obj.get("_pbtype") == "TSWP.StorageArchive":
                        t = obj.get("text", [])
                        if not t or all(not x for x in t if isinstance(x, str)):
                            from kpa.richtext import decode_storage
                            assert decode_storage(obj) == []
                            return
        pytest.skip("no empty TSWP.StorageArchive found")
    finally:
        deck.close()


def test_set_text_still_works_after_rich_text_added(tmp_path):
    """The legacy single-string set_text() must still work even though
    set_paragraphs() now exists."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        tb = _find_textblock(deck.slide[0], "807121")
        tb.set_text("just a single string")
        assert tb.text == "just a single string"
        out = deck.save(tmp_path / "legacy.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        tb2 = _find_textblock(deck2.slide[0], "807121")
        assert tb2.text == "just a single string"
    finally:
        deck2.close()
