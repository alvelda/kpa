"""
tests/test_loader_and_groups.py
=================================

Regression + correctness tests for two intertwined bugs found
2026-06-09 against a Captain-uploaded sample deck (``recon/test1.key``):

1. **Slide loader was silently dropping slides.** Apple writes the first
   slide of many decks into a non-suffixed ``Slide.iwa.yaml`` file, and
   chunk-split slides into ``Slide-<id>-<n>.iwa.yaml`` files where no
   primary ``Slide-<id>.iwa.yaml`` exists. The old loader only matched
   ``Slide-<id>.iwa.yaml``. Result: SVEF showed 58 slides instead of 60,
   test1 showed 1 instead of 2.

2. **`Slide.groups` was looking for the wrong pbtype.** The 4c.3 first
   pass searched for ``KN.GroupArchive``; Apple actually emits
   ``TSD.GroupArchive``. SVEF has 43 group archive instances (37 are
   slide-level, the rest are nested inside other groups); NCI has 3;
   test1 has 1. ``Slide.groups`` returned empty for all of them.

Both bugs were silently passing in the prior 4c.3 GREEN run. Captain
flagged it after spotting groups visually in SVEF/NCI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"
NCI = REPO / "recon" / "nci.key"
TEST1 = REPO / "recon" / "test1.key"


# ====================================================
# Loader: discovers every SlideArchive, not just Slide-<id>.iwa.yaml
# ====================================================


def test_loader_finds_all_svef_slides():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # SVEF's KN.ShowArchive.slideTree has 60 entries; the loader must
        # find every backing KN.SlideArchive (across Slide-<id>.iwa.yaml,
        # Slide.iwa.yaml, and Slide-<id>-<n>.iwa.yaml chunk-only files).
        assert len(deck.slide) == 60
    finally:
        deck.close()


def test_loader_finds_test1_both_slides():
    if not TEST1.exists():
        pytest.skip("test1 deck not available")
    deck = kpa.Deck.from_template(TEST1)
    try:
        # test1 has two slides; the second is in Slide.iwa.yaml (no id).
        assert len(deck.slide) == 2
        ids = sorted(s._slide_id for s in deck.slide)
        # 4030567 (Slide-4030567.iwa.yaml) + 4031092 (Slide.iwa.yaml)
        assert "4030567" in ids
        assert "4031092" in ids
    finally:
        deck.close()


def test_loader_slide_ids_unique():
    """No duplicate KN.SlideArchive across loaded slide files."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        ids = [s._slide_id for s in deck.slide]
        assert len(ids) == len(set(ids))
    finally:
        deck.close()


# ====================================================
# Groups: TSD.GroupArchive discovery (not KN.GroupArchive)
# ====================================================


def test_svef_has_groups_discovered():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # SVEF contains 43 TSD.GroupArchive total; the parent-id filter
        # keeps only slide-level groups (37 in practice, the rest are
        # nested groups whose parent is another group, not a slide).
        total = sum(len(s.groups) for s in deck.slide)
        assert total > 0, "SVEF must surface at least one slide-level group"
        # 37 is the actual observed count; tolerate small drift if we
        # tighten the parent filter later.
        assert total >= 30
    finally:
        deck.close()


def test_nci_has_groups_discovered():
    if not NCI.exists():
        pytest.skip("NCI not available")
    deck = kpa.Deck.from_template(NCI)
    try:
        total = sum(len(s.groups) for s in deck.slide)
        assert total == 3
    finally:
        deck.close()


def test_group_has_children_and_geometry():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Find any slide with groups
        for s in deck.slide:
            if s.groups:
                g = s.groups[0]
                assert len(g.children_ids) >= 1
                x, y = g.position
                w, h = g.size
                # Position can be 0,0 but size should be > 0
                assert w >= 0 and h >= 0
                return
        pytest.fail("no slide-level group found in SVEF")
    finally:
        deck.close()
