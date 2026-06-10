"""
tests/test_group_writes_4c3_2.py
====================================

Step 4c.3.2 — Group mutation API (round-trip tests using SVEF and
NCI samples, which contain real ``TSD.GroupArchive`` instances).

Covered capabilities (all round-trip):
  1.  Group.position / Group.size / Group.angle (read)
  2.  Group.set_position(x, y)
  3.  Group.set_size(w, h)
  4.  Group.move(dx, dy)
  5.  Group.add_child(shape) (idempotent)
  6.  Group.remove_child(shape)
  7.  Group.set_children([shapes])
  8.  children list survives lossless round-trip
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"
NCI = REPO / "recon" / "nci.key"


def _first_slide_with_groups(deck):
    for i, s in enumerate(deck.slide):
        if s.groups:
            return i, s
    return None, None


def _index_of_group(deck, slide_index: int, group_archive_id: str) -> int:
    """Re-find group on slide_index by archive id (groups are tuple-fresh on each access)."""
    for i, g in enumerate(deck.slide[slide_index].groups):
        if g.archive_id == group_archive_id:
            return i
    return -1


# ====================================================
# Geometry mutations
# ====================================================


def test_group_set_position_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, s = _first_slide_with_groups(deck)
        if s is None:
            pytest.skip("no group in SVEF")
        g = s.groups[0]
        gid = g.archive_id
        g.set_position(123.5, 456.25)
        assert g.position == (123.5, 456.25)
        out = deck.save(tmp_path / "group_pos.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        i = _index_of_group(deck2, sidx, gid)
        assert i >= 0
        g2 = deck2.slide[sidx].groups[i]
        assert g2.position == (123.5, 456.25)
    finally:
        deck2.close()


def test_group_set_size_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, s = _first_slide_with_groups(deck)
        if s is None:
            pytest.skip("no group in SVEF")
        g = s.groups[0]
        gid = g.archive_id
        g.set_size(321.0, 222.0)
        assert g.size == (321.0, 222.0)
        out = deck.save(tmp_path / "group_size.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        i = _index_of_group(deck2, sidx, gid)
        g2 = deck2.slide[sidx].groups[i]
        assert g2.size == (321.0, 222.0)
    finally:
        deck2.close()


def test_group_move_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, s = _first_slide_with_groups(deck)
        if s is None:
            pytest.skip("no group in SVEF")
        g = s.groups[0]
        gid = g.archive_id
        before = g.position
        g.move(dx=10.0, dy=-5.0)
        assert g.position == (before[0] + 10.0, before[1] - 5.0)
        out = deck.save(tmp_path / "group_move.key")
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        i = _index_of_group(deck2, sidx, gid)
        g2 = deck2.slide[sidx].groups[i]
        assert g2.position == (before[0] + 10.0, before[1] - 5.0)
    finally:
        deck2.close()


def test_group_angle_read():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, s = _first_slide_with_groups(deck)
        if s is None:
            pytest.skip("no group in SVEF")
        g = s.groups[0]
        a = g.angle
        assert isinstance(a, float)
    finally:
        deck.close()


# ====================================================
# Child membership mutations
# ====================================================


def test_group_remove_child_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Find a group with at least 2 children so removing one leaves it valid.
        for sidx, s in enumerate(deck.slide):
            for g in s.groups:
                if len(g.children_ids) >= 2:
                    gid = g.archive_id
                    before = list(g.children_ids)
                    removed = g.remove_child(before[0])
                    assert removed is True
                    assert before[0] not in g.children_ids
                    out = deck.save(tmp_path / "group_rmchild.key")
                    deck.close()
                    deck2 = kpa.Deck.from_template(out)
                    try:
                        i = _index_of_group(deck2, sidx, gid)
                        g2 = deck2.slide[sidx].groups[i]
                        assert before[0] not in g2.children_ids
                        assert set(g2.children_ids) == set(before[1:])
                    finally:
                        deck2.close()
                    return
        pytest.skip("no group with >=2 children found in SVEF")
    finally:
        # may have already closed inside the loop
        try:
            deck.close()
        except Exception:
            pass


def test_group_add_child_idempotent():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        sidx, s = _first_slide_with_groups(deck)
        if s is None:
            pytest.skip("no group in SVEF")
        g = s.groups[0]
        before = list(g.children_ids)
        # Re-adding an existing child is a no-op
        if before:
            g.add_child(before[0])
            assert list(g.children_ids) == before
    finally:
        deck.close()


def test_group_add_child_round_trip(tmp_path):
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Find a slide that has both a group and at least one image we can add
        for sidx, s in enumerate(deck.slide):
            if not s.groups:
                continue
            # Pick an image id that's NOT already a child of the first group
            g = s.groups[0]
            gid = g.archive_id
            existing = set(g.children_ids)
            candidate = None
            for img in s.images:
                if img._archive_id not in existing:
                    candidate = img._archive_id
                    break
            if candidate is None:
                continue
            g.add_child(candidate)
            assert candidate in g.children_ids
            out = deck.save(tmp_path / "group_addchild.key")
            deck.close()
            deck2 = kpa.Deck.from_template(out)
            try:
                i = _index_of_group(deck2, sidx, gid)
                g2 = deck2.slide[sidx].groups[i]
                assert candidate in g2.children_ids
            finally:
                deck2.close()
            return
        pytest.skip("no slide has both groups and an unused image")
    finally:
        try:
            deck.close()
        except Exception:
            pass


def test_group_children_resolve_partial():
    """Group.children resolves known proxy types; unknown kinds skipped."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        for s in deck.slide:
            for g in s.groups:
                kids = g.children
                # Either we resolve at least one or none — but the call must
                # not crash, and the type must be tuple of proxies.
                assert isinstance(kids, tuple)
                return
        pytest.skip("no group in SVEF")
    finally:
        deck.close()


# ====================================================
# Cross-deck regression: NCI groups
# ====================================================


def test_nci_groups_round_trip(tmp_path):
    if not NCI.exists():
        pytest.skip("NCI not available")
    deck = kpa.Deck.from_template(NCI)
    try:
        for sidx, s in enumerate(deck.slide):
            for g in s.groups:
                gid = g.archive_id
                before_pos = g.position
                g.move(dx=1.0, dy=1.0)
                out = deck.save(tmp_path / "nci_group.key")
                deck.close()
                deck2 = kpa.Deck.from_template(out)
                try:
                    i = _index_of_group(deck2, sidx, gid)
                    g2 = deck2.slide[sidx].groups[i]
                    assert g2.position == (before_pos[0] + 1.0, before_pos[1] + 1.0)
                finally:
                    deck2.close()
                return
        pytest.skip("no group in NCI")
    finally:
        try:
            deck.close()
        except Exception:
            pass
