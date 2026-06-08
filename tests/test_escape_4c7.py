"""
tests/test_escape_4c7.py
==========================

Step 4c.7 — Universal escape hatch (raw_archive / raw_get / raw_set /
raw_keys / raw_dump / raw_pbtype) on every proxy:

  TextBlock, Image, Slide, Build, Transition, Movie, Soundtrack,
  LiveVideoSource.

Also covers the path parser (kpa.escape.deep_get / deep_set), which is
the workhorse for raw_set's auto-create + auto-walk behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa import escape


REPO = Path(__file__).resolve().parent.parent


# =================== path parser ===================


def test_parse_path_empty():
    assert escape._parse_path("") == []


def test_parse_path_simple_keys():
    assert escape._parse_path("a.b.c") == [("key", "a"), ("key", "b"), ("key", "c")]


def test_parse_path_with_indices():
    assert escape._parse_path("a[0].b[3]") == [
        ("key", "a"), ("idx", 0), ("key", "b"), ("idx", 3)
    ]


def test_parse_path_mixed():
    assert escape._parse_path("super.objects[0].pbtype") == [
        ("key", "super"), ("key", "objects"), ("idx", 0), ("key", "pbtype")
    ]


def test_deep_get_simple():
    d = {"a": {"b": {"c": 42}}}
    assert escape.deep_get(d, "a.b.c") == 42
    assert escape.deep_get(d, "a.b.x", default=99) == 99
    assert escape.deep_get(d, "missing", default=None) is None


def test_deep_get_list_index():
    d = {"items": [{"k": "first"}, {"k": "second"}]}
    assert escape.deep_get(d, "items[1].k") == "second"
    assert escape.deep_get(d, "items[5].k", default=None) is None


def test_deep_set_creates_intermediate_dicts():
    d = {}
    escape.deep_set(d, "a.b.c", 42)
    assert d == {"a": {"b": {"c": 42}}}


def test_deep_set_raises_on_bad_list_index():
    d = {"items": [{"k": 1}]}
    with pytest.raises(ValueError, match="out of range"):
        escape.deep_set(d, "items[5].k", 99)


def test_deep_set_raises_on_empty_path():
    with pytest.raises(ValueError, match="empty path"):
        escape.deep_set({}, "", 1)


# =================== TextBlock raw access ===================


def test_textblock_raw_introspection():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = None
    for s in deck.slide[:10]:
        if s.texts:
            tb = s.texts[0]
            break
    assert tb is not None
    assert tb.raw_pbtype() == "TSWP.ShapeInfoArchive"
    keys = tb.raw_keys()
    assert "super" in keys
    # Geometry walk
    angle = tb.raw_get("super.super.geometry.angle")
    assert angle is not None
    # Dump returns a structure
    dump = tb.raw_dump(maxdepth=2)
    assert isinstance(dump, dict)
    print(f"\n  TextBlock pbtype={tb.raw_pbtype()} top_keys={keys[:4]} angle={angle}")
    deck.close()


def test_textblock_raw_set_round_trip(tmp_path):
    """Use raw_set to mutate a property the typed API also exposes
    (super.super.geometry.angle). Verify round-trip persistence."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tb = None
    sidx = None
    for i, s in enumerate(deck.slide[:10]):
        if s.texts:
            tb = s.texts[0]
            sidx = i
            break
    assert tb is not None
    tb.raw_set("super.super.geometry.angle", 17.5)
    out = tmp_path / "raw_tb.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    tb2 = deck2.slide[sidx].texts[0]
    angle = tb2.raw_get("super.super.geometry.angle")
    print(f"\n  TextBlock angle round-trip: -> {angle}")
    assert angle == pytest.approx(17.5)
    deck2.close()


# =================== Image raw access ===================


def test_image_raw_introspection():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    img = None
    for s in deck.slide[:20]:
        if s.images:
            img = s.images[0]
            break
    assert img is not None
    pb = img.raw_pbtype()
    assert pb in ("TSD.ImageArchive", "TSD.MovieArchive", "TSD.MediaArchive")
    print(f"\n  Image pbtype={pb}")
    deck.close()


# =================== Movie raw access ===================


def test_movie_raw_set_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    mv = None
    sidx = None
    for i, s in enumerate(deck.slide):
        if s.movies:
            mv = s.movies[0]
            sidx = i
            break
    assert mv is not None
    assert mv.raw_pbtype() == "TSD.MovieArchive"
    # Use a numeric field that's safe to mutate
    mv.raw_set("posterTime", 7.25)
    out = tmp_path / "raw_mv.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    mv2 = None
    for s in deck2.slide:
        if s.movies:
            mv2 = s.movies[0]; break
    assert mv2.raw_get("posterTime") == pytest.approx(7.25)
    print(f"\n  Movie posterTime via raw_set: {mv2.raw_get('posterTime')}")
    deck2.close()


# =================== Build raw access ===================


def test_build_raw_set_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    b = None
    sidx = None
    for i, s in enumerate(deck.slide):
        if s.builds:
            b = s.builds[0]
            sidx = i
            break
    assert b is not None
    assert b.raw_pbtype() == "KN.BuildArchive"
    # Mutate a deep field via raw API (test the path walker)
    b.raw_set("attributes.animationAttributes.duration", 4.5)
    out = tmp_path / "raw_build.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    b2 = deck2.slide[sidx].builds[0]
    dur = b2.raw_get("attributes.animationAttributes.duration")
    print(f"\n  Build duration via raw_set: -> {dur}")
    assert dur == pytest.approx(4.5)
    deck2.close()


# =================== Transition raw access ===================


def test_transition_raw_set_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    t = deck.slide[0].transition
    # Transition root is the .transition subtree
    t.raw_set("attributes.animationAttributes.duration", 3.75)
    out = tmp_path / "raw_trans.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    t2 = deck2.slide[0].transition
    dur = t2.raw_get("attributes.animationAttributes.duration")
    print(f"\n  Transition duration via raw_set: -> {dur}")
    assert dur == pytest.approx(3.75)
    deck2.close()


# =================== Soundtrack raw access ===================


def test_soundtrack_raw_set_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    st = deck.soundtrack
    assert st.raw_pbtype() == "KN.Soundtrack"
    st.raw_set("volume", 0.62)
    out = tmp_path / "raw_st.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    vol = deck2.soundtrack.raw_get("volume")
    print(f"\n  Soundtrack volume via raw_set: -> {vol}")
    assert vol == pytest.approx(0.62)
    deck2.close()


# =================== LiveVideoSource raw access ===================


def test_live_video_raw_set_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    lv = deck.live_video_sources[0]
    assert lv.raw_pbtype() == "KN.LiveVideoSource"
    lv.raw_set("name", "Front Studio Cam")
    out = tmp_path / "raw_lv.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    name = deck2.live_video_sources[0].raw_get("name")
    print(f"\n  LiveVideoSource name via raw_set: -> {name}")
    assert name == "Front Studio Cam"
    deck2.close()


# =================== Slide raw access ===================


def test_slide_raw_pbtype():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = deck.slide[0]
    assert s.raw_pbtype() == "KN.SlideArchive"
    keys = s.raw_keys()
    assert "ownedDrawables" in keys or "drawablesZOrder" in keys
    print(f"\n  Slide pbtype=KN.SlideArchive top_keys={keys[:5]}")
    deck.close()
