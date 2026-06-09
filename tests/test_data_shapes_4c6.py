"""
tests/test_data_shapes_4c6.py
==============================

Step 4c.6 (first pass) — read-only proxies for data shapes:

  * Chart (TSCH.ChartDrawableArchive)
  * Table (TST.TableInfoArchive) — schema introspection only,
    since SVEF/NCI have no on-slide table instances
  * Stylesheet enumeration helpers (chart styles + table styles)

Writes (series mutation, axis config, cell editing) are scoped to
4c.6.2 with a synthetic test deck.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa import escape
from kpa.shapes_data import (
    Chart,
    Table,
    list_chart_style_archive_ids,
    list_table_style_archive_ids,
)


REPO = Path(__file__).resolve().parent.parent


# =================== Path parser: bracketed extension keys ===================
# 4c.6 extension to kpa.escape: bracketed segments containing non-digit
# content are now dict keys (Apple's bracketed protobuf extension keys).
# Bracketed pure-digit segments remain list indices.

def test_parse_path_bracketed_extension_key():
    # Brackets are preserved in the key name to match the literal
    # dict key as it appears in YAML.
    assert escape._parse_path("[TSCH.ChartArchive.unity]") == [
        ("key", "[TSCH.ChartArchive.unity]")
    ]


def test_parse_path_bracketed_extension_in_middle():
    assert escape._parse_path("super.[TSCH.foo].bar") == [
        ("key", "super"), ("key", "[TSCH.foo]"), ("key", "bar")
    ]


def test_parse_path_mixed_list_index_and_bracketed_key():
    assert escape._parse_path("a.b[0].[ext.key]") == [
        ("key", "a"), ("key", "b"), ("idx", 0), ("key", "[ext.key]")
    ]


def test_parse_path_negative_list_index():
    assert escape._parse_path("a[-1].b") == [
        ("key", "a"), ("idx", -1), ("key", "b")
    ]


def test_deep_get_into_bracketed_key():
    d = {"[TSCH.foo]": {"inner": 42}}
    assert escape.deep_get(d, "[TSCH.foo].inner") == 42
    assert escape.deep_get(d, "[TSCH.foo].missing", default=99) == 99


# =================== Chart reads (SVEF) ===================


def test_charts_discovered_in_svef():
    """SVEF has 2 chart drawables (slides 1 and 4)."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    found = []
    for sidx, s in enumerate(deck.slide):
        for c in s.charts:
            found.append((sidx, c.archive_id))
    assert len(found) == 2, f"Expected 2 charts, found {len(found)}: {found}"
    print(f"\n  Found {len(found)} charts: {found}")
    deck.close()


def test_chart_pbtype_and_class():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    assert isinstance(chart, Chart)
    assert chart.raw_pbtype() == "TSCH.ChartDrawableArchive"
    assert Chart.PBTYPE == "TSCH.ChartDrawableArchive"
    print(f"\n  Chart pbtype confirmed: {chart.raw_pbtype()}")
    deck.close()


def test_chart_geometry_reads():
    """Position / size / angle / aspect_ratio_locked all read from the
    shared ``super`` TSD shape base."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    pos = chart.position
    sz = chart.size
    assert pos is not None and len(pos) == 2
    assert sz is not None and len(sz) == 2
    assert pos[0] > 0 and pos[1] > 0
    assert sz[0] > 0 and sz[1] > 0
    assert chart.angle == pytest.approx(0.0, abs=0.001)
    assert isinstance(chart.aspect_ratio_locked, bool)
    assert isinstance(chart.locked, bool)
    print(f"\n  Chart geometry: pos={pos}, size={sz}, angle={chart.angle}, "
          f"ar_locked={chart.aspect_ratio_locked}")
    deck.close()


def test_chart_unity_extension():
    """The bracketed ``[TSCH.ChartArchive.unity]`` extension holds the
    bulk of the chart schema. Confirm we can introspect it."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    assert chart.has_chart_unity is True
    keys = chart.chart_unity_keys
    assert len(keys) > 0
    # The canonical preserve-appearance extension should be present
    expected = "[TSCH.ChartPreserveAppearanceForPresetArchive.appearance_preserved_for_preset]"
    assert expected in keys, f"Expected {expected} in unity keys; got first 3: {keys[:3]}"
    print(f"\n  Chart unity has {len(keys)} extension sub-keys")
    deck.close()


def test_chart_raw_keys_top_level():
    """``raw_keys()`` on a chart drawable returns the top-level dict
    keys including the bracketed extension."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    keys = chart.raw_keys()
    assert "_pbtype" in keys
    assert "super" in keys
    assert "[TSCH.ChartArchive.unity]" in keys
    print(f"\n  raw_keys() = {keys}")
    deck.close()


def test_chart_escape_hatch_deep_get():
    """Use the universal escape hatch to walk into a real chart
    extension sub-key."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    # The unity block exists; walk into it
    unity = chart.raw_get("[TSCH.ChartArchive.unity]")
    assert unity is not None
    assert isinstance(unity, dict)
    # Should have at least one preserve-appearance preset
    preserve = chart.raw_get(
        "[TSCH.ChartArchive.unity].[TSCH.ChartPreserveAppearanceForPresetArchive.appearance_preserved_for_preset]"
    )
    # NB: even if None it should not raise — the escape hatch tolerates
    # missing leaves gracefully
    print(f"\n  unity is dict with {len(unity)} keys; preserve preset = {type(preserve).__name__}")
    deck.close()


def test_chart_repr():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    chart = None
    for s in deck.slide:
        if s.charts:
            chart = s.charts[0]
            break
    assert chart is not None
    r = repr(chart)
    assert r.startswith("<Chart #")
    assert chart.archive_id in r
    print(f"\n  repr: {r}")
    deck.close()


def test_chart_geometry_round_trip(tmp_path):
    """Save/open round-trip: chart geometry must survive a pack+unpack.

    This is a parity check, not a mutation — we don't have a chart
    write API yet, but the read path must survive lossless save.
    """
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    before = []
    for s in deck.slide:
        for c in s.charts:
            before.append((c.archive_id, c.position, c.size))
    out = tmp_path / "chart_rt.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    after = []
    for s in deck2.slide:
        for c in s.charts:
            after.append((c.archive_id, c.position, c.size))
    assert before == after, f"Geometry drift: {before} vs {after}"
    print(f"\n  Chart geometry round-tripped clean for {len(before)} charts")
    deck2.close()


# =================== Table reads ===================


def test_tables_class_introspection():
    """Tables don't appear as drawables in SVEF/NCI, so this is a
    class-level sanity check + empty-list contract.
    """
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    total = 0
    for s in deck.slide:
        assert isinstance(s.tables, tuple)
        total += len(s.tables)
    assert total == 0, f"SVEF should have no on-slide tables; got {total}"
    assert Table.PBTYPE == "TST.TableInfoArchive"
    print(f"\n  SVEF: {total} on-slide tables (expected 0)")
    deck.close()


# =================== Stylesheet enumeration (TST + TSCH) ===================


def test_stylesheet_table_styles_enumerable():
    """The DocumentStylesheet holds TST.TableStyleArchive templates
    (named table styles users see in Keynote's style chooser).
    Enumerate them for brand-validator use."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    ids = list_table_style_archive_ids(deck)
    assert len(ids) > 0, "Expected at least one TST.TableStyleArchive in SVEF stylesheet"
    assert all(isinstance(i, str) for i in ids)
    print(f"\n  SVEF stylesheet has {len(ids)} table styles (first 3: {ids[:3]})")
    deck.close()


def test_stylesheet_chart_styles_enumerable():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    ids = list_chart_style_archive_ids(deck)
    assert len(ids) > 0, "Expected at least one TSCH.ChartStyleArchive in SVEF stylesheet"
    print(f"\n  SVEF stylesheet has {len(ids)} chart styles (first 3: {ids[:3]})")
    deck.close()


def test_stylesheet_iter_by_pbtype_helper():
    """Confirm the underlying Stylesheet.iter_by_pbtype helper works
    for arbitrary pbtypes (used by both list_* convenience functions
    and any future brand-validator)."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sheet = deck.stylesheet
    assert sheet is not None
    # Count various pbtypes
    n_table = sum(1 for _ in sheet.iter_by_pbtype("TST.TableStyleArchive"))
    n_cell = sum(1 for _ in sheet.iter_by_pbtype("TST.CellStyleArchive"))
    n_chart = sum(1 for _ in sheet.iter_by_pbtype("TSCH.ChartStyleArchive"))
    n_unknown = sum(1 for _ in sheet.iter_by_pbtype("XYZ.NoSuchArchive"))
    assert n_table > 0
    assert n_cell > 0
    assert n_chart > 0
    assert n_unknown == 0
    print(f"\n  TST.TableStyleArchive: {n_table}, TST.CellStyleArchive: {n_cell}, "
          f"TSCH.ChartStyleArchive: {n_chart}, unknown: {n_unknown}")
    deck.close()
