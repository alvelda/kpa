"""
tests/test_table_writes_4c6_2.py
==================================

Step 4c.6.2-tables — On-slide tables. Builds on the deck-wide cross-file
archive index added in 4c.6.2 (``Deck._by_parent_index``).

Apple stores ``TST.TableInfoArchive`` for on-slide tables in
``CalculationEngine.iwa.yaml``, with ``super.parent.identifier``
pointing at the owning slide. The per-slide-file archive scan
introduced in 4c.6 cannot reach these — so ``Slide.tables`` returned
empty for every deck in the corpus that actually had a table on a
slide.

Covered capabilities (all round-trip):

  1. Slide.tables discovers cross-file table archives
  2. Table.position / Table.size / Table.angle (read)
  3. Table.set_position(x, y) (round-trip via aux-file flush)
  4. Table.set_size(w, h)
  5. Table.move(dx, dy)
  6. Table.table_model_id / Table.summary_model_id (reference ids
     surfaced for escape-hatch cell work)
  7. Escape hatch on Table reaches arbitrary fields
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"
TEST1 = REPO / "recon" / "test1.key"


def _first_slide_with_tables(deck):
    for i, s in enumerate(deck.slide):
        if s.tables:
            return i, s
    return None, None


# ============= discovery =============


def test_test1_has_one_table():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        tables_by_slide = [(i, len(s.tables)) for i, s in enumerate(deck.slide) if s.tables]
        assert tables_by_slide == [(1, 1)], (
            f"expected one table on slide 1, got {tables_by_slide}"
        )
    finally:
        deck.close()


def test_svef_has_three_tables():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        total = sum(len(s.tables) for s in deck.slide)
        assert total == 3
    finally:
        deck.close()


def test_table_references_table_model():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        _, s = _first_slide_with_tables(deck)
        assert s is not None
        t = s.tables[0]
        tm = t.table_model_id
        sm = t.summary_model_id
        assert tm is not None and tm.isdigit()
        assert sm is not None and sm.isdigit()
    finally:
        deck.close()


# ============= geometry reads =============


def test_table_position_size_angle_read():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        _, s = _first_slide_with_tables(deck)
        t = s.tables[0]
        pos = t.position
        sz = t.size
        a = t.angle
        assert pos is not None
        assert sz is not None
        assert isinstance(a, float)
        # known sane values for the test1 table
        assert sz[0] > 0 and sz[1] > 0
    finally:
        deck.close()


# ============= geometry mutation (cross-file flush) =============


def test_table_set_position_round_trip(tmp_path):
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        sidx, s = _first_slide_with_tables(deck)
        t = s.tables[0]
        tid = t._archive_id
        t.set_position(111.0, 222.0)
        assert t.position == (111.0, 222.0)
        out = deck.save(tmp_path / "table_pos.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        # Re-find by archive id
        for t2 in deck2.slide[sidx].tables:
            if t2._archive_id == tid:
                assert t2.position == (111.0, 222.0)
                return
        pytest.fail("table not found after round-trip")
    finally:
        deck2.close()


def test_table_set_size_round_trip(tmp_path):
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        sidx, s = _first_slide_with_tables(deck)
        t = s.tables[0]
        tid = t._archive_id
        t.set_size(700.0, 400.0)
        assert t.size == (700.0, 400.0)
        out = deck.save(tmp_path / "table_size.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        for t2 in deck2.slide[sidx].tables:
            if t2._archive_id == tid:
                assert t2.size == (700.0, 400.0)
                return
        pytest.fail("table not found after round-trip")
    finally:
        deck2.close()


def test_table_move_round_trip(tmp_path):
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        sidx, s = _first_slide_with_tables(deck)
        t = s.tables[0]
        tid = t._archive_id
        before = t.position
        t.move(dx=15.0, dy=25.0)
        assert t.position == (before[0] + 15.0, before[1] + 25.0)
        out = deck.save(tmp_path / "table_move.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        for t2 in deck2.slide[sidx].tables:
            if t2._archive_id == tid:
                assert t2.position == (before[0] + 15.0, before[1] + 25.0)
                return
        pytest.fail("table not found after round-trip")
    finally:
        deck2.close()


# ============= escape hatch =============


def test_table_escape_hatch():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        _, s = _first_slide_with_tables(deck)
        t = s.tables[0]
        # Read a deep value
        ft = t.raw_get("formulaCoordSpace")
        assert ft is not None
    finally:
        deck.close()
