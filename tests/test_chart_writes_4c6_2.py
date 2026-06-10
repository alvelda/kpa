"""
tests/test_chart_writes_4c6_2.py
==================================

Step 4c.6.2 — Chart mutation API (typed write accessors on top of the
read-only 4c.6 first pass).

Covered capabilities (all round-trip):

  1.  Chart.chart_type            (str setter)
  2.  Chart.chart_style_id        (str setter)
  3.  Chart.column_names          (list[str] setter, length-locked)
  4.  Chart.row_names             (list[str] setter, length-locked)
  5.  Chart.series_values         (list[float|None] setter, length-locked)
  6.  Chart.set_position(x, y)
  7.  Chart.set_size(w, h)
  8.  Chart.move(dx, dy)
  9.  Chart.mark_dirty_for_recompute()
  10. Length-mismatch validation raises ValueError (no silent corruption)

Table mutation (cell read/write) is deferred until a sample deck with
a real TST.TableInfoArchive lands in recon/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"


def _first_chart(deck):
    """Return the first chart found in the deck, or None."""
    for s in deck.slide:
        if s.charts:
            return s.charts[0]
    return None


# =================== read-side sanity (regression) ===================


def test_chart_read_side_still_works():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        assert c is not None
        assert c.chart_type is not None
        assert len(c.column_names) > 0
        assert len(c.row_names) > 0
        assert c.series_count() >= 1
        vals = c.series_values(0)
        assert len(vals) == len(c.column_names)
    finally:
        deck.close()


# =================== chart_type ===================


def test_chart_type_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        original = c.chart_type
        c.set_chart_type("barChartType2D")
        assert c.chart_type == "barChartType2D"
        out = deck.save(tmp_path / "chart_type.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.chart_type == "barChartType2D"
        assert c2.chart_type != original
    finally:
        deck2.close()


def test_chart_type_rejects_empty_or_none():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        with pytest.raises(ValueError):
            c.set_chart_type("")
        with pytest.raises(ValueError):
            c.set_chart_type(None)  # type: ignore[arg-type]
    finally:
        deck.close()


# =================== chart_style_id ===================


def test_chart_style_id_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        # Pick an arbitrary other chart-style id from the stylesheet.
        from kpa.shapes_data import list_chart_style_archive_ids
        ids = [i for i in list_chart_style_archive_ids(deck) if i != c.chart_style_id]
        if not ids:
            pytest.skip("no alternative chart styles available")
        target = ids[0]
        c.set_chart_style_id(target)
        assert c.chart_style_id == target
        out = deck.save(tmp_path / "chart_style.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.chart_style_id == target
    finally:
        deck2.close()


# =================== column_names + row_names ===================


def test_column_names_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        new = [f"Col{i}" for i in range(len(c.column_names))]
        c.set_column_names(new)
        assert list(c.column_names) == new
        out = deck.save(tmp_path / "cols.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert list(c2.column_names) == new
    finally:
        deck2.close()


def test_column_names_length_locked():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.column_names)
        with pytest.raises(ValueError):
            c.set_column_names([f"Col{i}" for i in range(n + 1)])
        with pytest.raises(ValueError):
            c.set_column_names([f"Col{i}" for i in range(max(0, n - 1))])
    finally:
        deck.close()


def test_row_names_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        new = [f"Series{i}" for i in range(len(c.row_names))]
        c.set_row_names(new)
        assert list(c.row_names) == new
        out = deck.save(tmp_path / "rows.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert list(c2.row_names) == new
    finally:
        deck2.close()


def test_row_names_length_locked():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.row_names)
        with pytest.raises(ValueError):
            c.set_row_names([f"S{i}" for i in range(n + 1)])
    finally:
        deck.close()


# =================== series_values ===================


def test_series_values_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.column_names)
        new_vals = [float(i * 10 + 1) for i in range(n)]
        c.set_series_values(new_vals, row_index=0)
        got = c.series_values(0)
        assert list(got) == new_vals
        out = deck.save(tmp_path / "series.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert list(c2.series_values(0)) == new_vals
    finally:
        deck2.close()


def test_series_values_allows_none_blanks(tmp_path):
    """``None`` cells write as empty dicts and read back as ``None``."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.column_names)
        if n < 2:
            pytest.skip("need >=2 columns")
        new_vals: list[float | None] = [1.0, None] + [float(i + 2) for i in range(n - 2)]
        c.set_series_values(new_vals, row_index=0)
        got = c.series_values(0)
        assert got[0] == 1.0
        assert got[1] is None
        out = deck.save(tmp_path / "series_blanks.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        got2 = c2.series_values(0)
        assert got2[0] == 1.0
        assert got2[1] is None
    finally:
        deck2.close()


def test_series_values_length_locked():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.column_names)
        with pytest.raises(ValueError):
            c.set_series_values([1.0] * (n + 1), row_index=0)
        with pytest.raises(ValueError):
            c.set_series_values([1.0] * max(0, n - 1), row_index=0)
    finally:
        deck.close()


def test_series_values_invalid_row_raises():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = c.series_count()
        with pytest.raises(IndexError):
            c.series_values(n + 5)
    finally:
        deck.close()


# =================== geometry setters ===================


def test_chart_set_position_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        c.set_position(200.0, 300.0)
        assert c.position == (200.0, 300.0)
        out = deck.save(tmp_path / "chart_pos.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.position == (200.0, 300.0)
    finally:
        deck2.close()


def test_chart_set_size_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        c.set_size(450.0, 275.0)
        assert c.size == (450.0, 275.0)
        out = deck.save(tmp_path / "chart_size.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.size == (450.0, 275.0)
    finally:
        deck2.close()


def test_chart_move_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        before = c.position
        c.move(dx=50.0, dy=-25.0)
        assert c.position == (before[0] + 50.0, before[1] - 25.0)
        out = deck.save(tmp_path / "chart_move.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.position[0] == pytest.approx(before[0] + 50.0, abs=1e-3)
        assert c2.position[1] == pytest.approx(before[1] - 25.0, abs=1e-3)
    finally:
        deck2.close()


# =================== mark_dirty_for_recompute ===================


def test_mark_dirty_for_recompute_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        # Force-flip to False first
        c._unity()["isDirty"] = False
        c.mark_dirty_for_recompute()
        assert c.raw_get("[TSCH.ChartArchive.unity].isDirty") is True
        out = deck.save(tmp_path / "chart_dirty.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.raw_get("[TSCH.ChartArchive.unity].isDirty") is True
    finally:
        deck2.close()


# =================== combined "redesign chart" round-trip ===================


def test_chart_full_redesign_round_trip(tmp_path):
    """One save/open exercising every chart mutator at once. This is
    the F2-edit gate for charts (one of the five named edits in the
    PRD surgical-edit suite, generalised to chart mutation)."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        c = _first_chart(deck)
        n = len(c.column_names)
        if n < 4:
            pytest.skip("need 4+ columns for the full redesign")
        c.set_chart_type("columnChartType2D")
        c.set_column_names(["Jan", "Feb", "Mar", "Apr"] + list(c.column_names[4:]))
        c.set_row_names(["Revenue"] + list(c.row_names[1:]))
        c.set_series_values([10.0, 20.0, 30.0, 40.0] + list(c.series_values(0)[4:]),
                            row_index=0)
        c.set_position(75.0, 150.0)
        c.set_size(525.0, 325.0)
        c.mark_dirty_for_recompute()
        out = deck.save(tmp_path / "redesign.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        c2 = _first_chart(deck2)
        assert c2.chart_type == "columnChartType2D"
        assert c2.column_names[:4] == ("Jan", "Feb", "Mar", "Apr")
        assert c2.row_names[0] == "Revenue"
        assert list(c2.series_values(0)[:4]) == [10.0, 20.0, 30.0, 40.0]
        assert c2.position == (75.0, 150.0)
        assert c2.size == (525.0, 325.0)
        assert c2.raw_get("[TSCH.ChartArchive.unity].isDirty") is True
    finally:
        deck2.close()
