"""
tests/test_table_cells_4c6_3.py
=================================

Step 4c.6.3 \u2014 TST cell read/write codec.

Decodes the TST.Tile.cellStorageBuffer binary payload (storageVersion=5)
discovered in recon/test1.key and recon/svef.key. Covers:

  - cell read (string / int / currency) on both 24-byte and 32-byte
    string record variants
  - Table.values() returning the 2-D Python view
  - String cell write (round-trip; new string interned in stringTable)
  - Int cell write (round-trip; u64 LE replacement at byte offset 12)
  - Currency cell write (round-trip; u64 LE at byte offset 12)
  - Length-preserving type guard (can't rewrite a string cell as int
    without corrupting downstream cells)
  - num_rows / num_cols accessors

Test fixtures:
  - recon/test1.key (3x4 all-string table on slide 1)
  - recon/svef.key (10x12 mixed-type table on slide 17; 10x3 long-cell
    table on slide 5)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"
TEST1 = REPO / "recon" / "test1.key"


def _find_table(deck, rows=None, cols=None):
    for i, s in enumerate(deck.slide):
        for t in s.tables:
            if (rows is None or t.num_rows == rows) and (cols is None or t.num_cols == cols):
                return i, t
    return None, None


# ============= cell read =============


def test_test1_cell_values():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        assert t.num_rows == 3
        assert t.num_cols == 4
        v = t.values()
        # Just verify the header row reads back as strings
        assert all(isinstance(x, str) for x in v[0])
        assert v[0][0] == "this is a table"
        assert v[1][1] == "qwerqweq"
    finally:
        deck.close()


def test_svef_int_currency_cell_read():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        _, t = _find_table(deck, rows=10, cols=12)
        assert t is not None, "10x12 funds table not found"
        v = t.values()
        # First data row: Amadeus V Technology Fund, year 2018, fund size 146M, 22 companies
        assert v[1][0] == "Amadeus V Technology Fund"
        assert v[1][1] == 2018
        assert v[1][2] == 146_000_000
        assert v[1][3] == 22
    finally:
        deck.close()


def test_cell_method_returns_decoded_cell():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        c = t.cell(1, 0)
        assert c is not None
        assert c.kind == "string"
        assert c.value == "drawer"
    finally:
        deck.close()


# ============= cell write \u2014 round-trip =============


def test_string_cell_write_round_trip(tmp_path):
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        t.set_cell_string(1, 0, "EDITED_BY_KPA")
        assert t.cell(1, 0).value == "EDITED_BY_KPA"
        out = deck.save(tmp_path / "test1_str.key")
    finally:
        deck.close()
    deck2 = kpa.Deck.from_template(out)
    try:
        t2 = deck2.slide[1].tables[0]
        assert t2.cell(1, 0).value == "EDITED_BY_KPA"
        # Other cells preserved
        assert t2.cell(0, 0).value == "this is a table"
        assert t2.cell(2, 3).value == "were"
    finally:
        deck2.close()


def test_int_cell_write_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, t = _find_table(deck, rows=10, cols=12)
        # Vintage Year col=1, first data row=1: 2018 -> 2042
        t.set_cell_int(1, 1, 2042)
        # Companies col=3, row 1: 22 -> 99
        t.set_cell_int(1, 3, 99)
        out = deck.save(tmp_path / "svef_int.key")
    finally:
        deck.close()
    deck2 = kpa.Deck.from_template(out)
    try:
        _, t2 = _find_table(deck2, rows=10, cols=12)
        v = t2.values()
        assert v[1][1] == 2042
        assert v[1][3] == 99
        # untouched cell preserved
        assert v[1][0] == "Amadeus V Technology Fund"
    finally:
        deck2.close()


def test_currency_cell_write_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        _, t = _find_table(deck, rows=10, cols=12)
        # Fund Size col=2, row 1: 146M -> 500M
        t.set_cell_currency(1, 2, 500_000_000)
        out = deck.save(tmp_path / "svef_cur.key")
    finally:
        deck.close()
    deck2 = kpa.Deck.from_template(out)
    try:
        _, t2 = _find_table(deck2, rows=10, cols=12)
        assert t2.values()[1][2] == 500_000_000
    finally:
        deck2.close()


def test_multiple_cell_writes_in_one_save(tmp_path):
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        t.set_cell_string(0, 0, "HDR1")
        t.set_cell_string(0, 1, "HDR2")
        t.set_cell_string(2, 3, "TAIL")
        out = deck.save(tmp_path / "test1_multi.key")
    finally:
        deck.close()
    deck2 = kpa.Deck.from_template(out)
    try:
        t2 = deck2.slide[1].tables[0]
        v = t2.values()
        assert v[0][0] == "HDR1"
        assert v[0][1] == "HDR2"
        assert v[2][3] == "TAIL"
        # Untouched cells preserved
        assert v[1][0] == "drawer"
        assert v[1][2] == "why me"
    finally:
        deck2.close()


# ============= type guards =============


def test_set_int_on_string_cell_raises():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        with pytest.raises(ValueError, match="INT-typed"):
            t.set_cell_int(1, 0, 42)
    finally:
        deck.close()


def test_set_string_on_int_cell_raises():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        _, t = _find_table(deck, rows=10, cols=12)
        with pytest.raises(ValueError, match="STRING-typed"):
            t.set_cell_string(1, 1, "not allowed")
    finally:
        deck.close()


def test_out_of_range_cell_raises():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        t = deck.slide[1].tables[0]
        with pytest.raises(IndexError):
            t.cell(0, 99)
        with pytest.raises(IndexError):
            t.cell(99, 0)
    finally:
        deck.close()
