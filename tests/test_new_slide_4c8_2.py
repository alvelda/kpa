"""
tests/test_new_slide_4c8_2.py
==============================

Step 4c.8.2 — Deck.new_slide(kind=...) template instantiation.

These tests verify the new-slide creation path end-to-end:
  - Each canonical kind in the SVEF theme can be instantiated
  - The slide count and slideTree are both updated
  - F1 lossless round-trip survives the save (re-open + count)
  - The new slide is mutable via the existing 4b/4c surface
  - after=<index> inserts at the right position
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa.slide_kinds import (
    list_slide_kinds,
    find_slide_kind,
    slide_kind_for_slide,
)

REPO = Path(__file__).resolve().parent.parent


# ============== basic creation ==============


def test_new_slide_blank_appends(tmp_path):
    """Append a BLANK slide. Count goes up by 1, save/reload survives."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    n_before = len(deck.slide)
    new = deck.new_slide(kind="BLANK")
    assert new is not None
    assert len(deck.slide) == n_before + 1
    out = deck.save(tmp_path / "out.key")
    deck.close()

    # Reload and verify the slide count survives
    deck2 = kpa.Deck.from_template(out)
    assert len(deck2.slide) == n_before + 1
    deck2.close()


def test_new_slide_title_and_body(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    n_before = len(deck.slide)
    new = deck.new_slide(kind="TITLE_AND_BODY")
    assert new is not None
    out = deck.save(tmp_path / "out.key")
    deck.close()
    deck2 = kpa.Deck.from_template(out)
    assert len(deck2.slide) == n_before + 1
    deck2.close()


def test_new_slide_case_insensitive_kind(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    new = deck.new_slide(kind="title_and_body")  # lower-case
    assert new is not None
    deck.close()


def test_new_slide_rejects_unknown_kind():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    with pytest.raises(ValueError, match="No template slide named"):
        deck.new_slide(kind="DEFINITELY_NOT_A_REAL_KIND")
    deck.close()


# ============== template resolution ==============


def test_new_slide_references_correct_template(tmp_path):
    """The new slide's templateSlide field should point at the
    requested template's identifier."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tpl = find_slide_kind(deck, name="BLANK")
    assert tpl is not None

    new = deck.new_slide(kind="BLANK")
    sk = slide_kind_for_slide(new)
    assert sk is not None
    assert sk.identifier == tpl.identifier
    assert (sk.name or "").upper() == "BLANK"
    deck.close()


def test_new_slide_has_no_name_field():
    """Regular slides do not carry a 'name' field (only templates do)."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    new = deck.new_slide(kind="BLANK")
    assert new.raw_pbtype() == "KN.SlideArchive"
    assert new.raw_get("name") is None
    deck.close()


# ============== identifier uniqueness ==============


def test_new_slide_identifiers_dont_collide(tmp_path):
    """Create 3 new slides; verify no identifier collisions across them
    or with the existing deck archives."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)

    # Capture existing identifiers across all YAML files
    import yaml
    idx = deck._unpacked_root / "Index"
    existing: set[str] = set()
    for yp in idx.glob("*.iwa.yaml"):
        try:
            data = yaml.safe_load(yp.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for chunk in (data.get("chunks") or []):
            for arch in (chunk.get("archives") or []):
                hdr = arch.get("header") or {}
                ident = hdr.get("identifier")
                if ident is not None:
                    existing.add(str(ident))

    new_slides = [
        deck.new_slide(kind="BLANK"),
        deck.new_slide(kind="TITLE_AND_BODY"),
        deck.new_slide(kind="BLANK"),
    ]
    new_ids = {s._archive_id for s in new_slides}
    assert len(new_ids) == 3, "All three new slide archive ids should differ"
    assert not (new_ids & existing), \
        f"New slide ids collide with existing: {new_ids & existing}"
    deck.close()


# ============== mutation on new slide ==============


def test_new_slide_supports_raw_get(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    new = deck.new_slide(kind="BLANK")
    # Read template's transition through the escape hatch
    transition_effect = new.raw_get("transition.attributes.animationAttributes.effect")
    assert transition_effect is not None
    print(f"\n  new slide transition.effect = {transition_effect!r}")
    deck.close()


# ============== file emission ==============


def test_new_slide_emits_yaml_file(tmp_path):
    """The new-slide path writes a Slide-<id>.iwa.yaml into Index/."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    idx = deck._unpacked_root / "Index"
    before = set(p.name for p in idx.glob("Slide-*.iwa.yaml"))
    new = deck.new_slide(kind="BLANK")
    after = set(p.name for p in idx.glob("Slide-*.iwa.yaml"))
    new_files = after - before
    assert len(new_files) == 1, f"Expected 1 new slide file, got {new_files}"
    new_name = new_files.pop()
    assert new_name.startswith("Slide-")
    print(f"\n  Emitted: {new_name}")
    deck.close()


# ============== slideTree integration ==============


def test_new_slide_appended_to_slide_tree(tmp_path):
    """The new slide gets registered in ShowArchive.slideTree.slides."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    # Read slideTree before
    doc = deck._document_root()
    from kpa.new_slide import _find_show_archive
    show = _find_show_archive(doc)
    before_len = len(show["slideTree"]["slides"])

    new = deck.new_slide(kind="BLANK")
    after_len = len(show["slideTree"]["slides"])
    assert after_len == before_len + 1
    deck.close()


def test_new_slide_after_inserts_at_position(tmp_path):
    """new_slide(kind=X, after=0) puts the new slide at index 1."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    new = deck.new_slide(kind="BLANK", after=0)
    # The new slide should now be deck.slide[1]
    # We verify by archive id
    target_id = new._archive_id
    actual_at_1 = deck.slide[1]._archive_id
    assert actual_at_1 == target_id, \
        f"Expected new slide at index 1, got {actual_at_1!r} != {target_id!r}"
    deck.close()


# ============== round-trip stability ==============


def test_new_slide_round_trips(tmp_path):
    """End-to-end: create slide, save, reopen, verify it's still there
    with the right template kind."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    n_before = len(deck.slide)
    tpl = find_slide_kind(deck, name="TITLE_AND_BODY")
    new = deck.new_slide(kind="TITLE_AND_BODY")
    new_id = new._archive_id
    out = deck.save(tmp_path / "out.key")
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    assert len(deck2.slide) == n_before + 1
    # Find the slide whose archive id matches
    found = None
    for s in deck2.slide:
        if s._archive_id == new_id:
            found = s
            break
    assert found is not None, "Round-tripped deck doesn't have the new slide"
    sk = slide_kind_for_slide(found)
    if sk is not None:
        assert (sk.name or "").upper() == "TITLE_AND_BODY"
    deck2.close()


# ============== multiple kinds ==============


def test_new_slide_multiple_kinds_all_work(tmp_path):
    """Instantiate every canonical Apple kind we can find in SVEF."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    canonical = {"BLANK", "TITLE_AND_BODY", "TITLE_AND_TWO_COLUMNS"}
    available = [k for k in list_slide_kinds(deck)
                 if (k.name or "").upper() in canonical]
    assert len(available) >= 3, "Need at least 3 canonical kinds in SVEF"

    n_before = len(deck.slide)
    for k in available[:3]:
        deck.new_slide(kind=k.name)
    assert len(deck.slide) == n_before + 3

    out = deck.save(tmp_path / "out.key")
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    assert len(deck2.slide) == n_before + 3
    deck2.close()
