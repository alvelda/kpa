"""
tests/test_layout_4c3.py
==========================

Step 4c.3 — Slide layout / structure: z-order operations and Group
proxy. Z-order lives on ``KN.SlideArchive.drawablesZOrder`` and is the
foundation for "bring to front", "send to back", and reorder UX.

Capability table (this step):

  1.  Slide.drawables_z_order               (read)
  2.  Slide.z_index(shape)                  (lookup)
  3.  Slide.bring_to_front(shape)           (mutate)
  4.  Slide.send_to_back(shape)             (mutate)
  5.  Slide.send_forward(shape)             (mutate, +1)
  6.  Slide.send_backward(shape)            (mutate, -1)
  7.  Slide.set_z_order([shape, ...])       (explicit replace)
  8.  Slide.groups                          (read; empty when absent)
  9.  Group.children_ids / Group.children   (read)
  10. Round-trip: z-order mutation persists across save/open

All ops accept a TextBlock, Image, raw archive id (str/int), or a
``{identifier: <id>}`` dict.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa.layout import Group


REPO = Path(__file__).resolve().parent.parent
SVEF = REPO / "recon" / "svef.key"


# ============================================================
# Read-side: drawables_z_order + z_index + groups
# ============================================================


def test_drawables_z_order_returns_tuple_of_ids():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        zo = s.drawables_z_order
        assert isinstance(zo, tuple)
        assert len(zo) > 0
        # Every entry is a string id
        for entry in zo:
            assert isinstance(entry, str)
            assert entry.isdigit() or entry  # non-empty
        print(f"\n  slide[0] z-order count: {len(zo)}")
        print(f"  first 3: {zo[:3]}")
    finally:
        deck.close()


def test_z_index_lookup():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        zo = s.drawables_z_order
        assert s.z_index(zo[0]) == 0
        assert s.z_index(zo[-1]) == len(zo) - 1
        # Missing shape returns -1
        assert s.z_index("999999999") == -1
        # Resolver accepts ints
        assert s.z_index(int(zo[0])) == 0
        # And dicts
        assert s.z_index({"identifier": zo[0]}) == 0
    finally:
        deck.close()


def test_groups_empty_on_svef():
    """SVEF + NCI don't use groups; empty tuple is the right answer."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Scan first 10 slides — none should have groups in our samples
        for s in deck.slide[:10]:
            assert s.groups == ()
    finally:
        deck.close()


# ============================================================
# Mutate-side (in-memory; round-trip below)
# ============================================================


def test_bring_to_front_in_memory():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = s.drawables_z_order
        target = original[0]
        ok = s.bring_to_front(target)
        assert ok is True
        new = s.drawables_z_order
        assert new[-1] == target
        assert len(new) == len(original)
        # All ids preserved
        assert set(new) == set(original)
        # Idempotent: front-of-front is a no-op
        assert s.bring_to_front(target) is False
    finally:
        deck.close()


def test_send_to_back_in_memory():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = s.drawables_z_order
        target = original[-1]
        ok = s.send_to_back(target)
        assert ok is True
        new = s.drawables_z_order
        assert new[0] == target
        assert set(new) == set(original)
        # Idempotent
        assert s.send_to_back(target) is False
    finally:
        deck.close()


def test_send_forward_backward_in_memory():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = s.drawables_z_order
        # Pick something in the middle
        target = original[5]
        before = s.z_index(target)
        s.send_forward(target)
        assert s.z_index(target) == before + 1
        s.send_backward(target)
        assert s.z_index(target) == before
        # Backing up past 0 clamps + reports no-change
        s.send_to_back(target)
        assert s.send_backward(target) is False
        # Forwarding past end clamps
        s.bring_to_front(target)
        assert s.send_forward(target) is False
    finally:
        deck.close()


def test_set_z_order_explicit():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = list(s.drawables_z_order)
        # Reverse order
        ok = s.set_z_order(list(reversed(original)))
        assert ok is True
        assert list(s.drawables_z_order) == list(reversed(original))
        # Partial reorder: pass just the first 3 — they should land at
        # the back; the remaining ids stay in their previous order.
        partial = original[:3]
        s.set_z_order(partial)
        new = list(s.drawables_z_order)
        assert new[:3] == partial
        assert set(new) == set(original)
    finally:
        deck.close()


def test_set_z_order_noop_returns_false():
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        same = list(s.drawables_z_order)
        assert s.set_z_order(same) is False
    finally:
        deck.close()


def test_zorder_accepts_proxy_objects():
    """bring_to_front / send_to_back must accept TextBlock/Image proxies
    directly, not just raw ids."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        # Find a slide whose first text-block IS in drawablesZOrder.
        # (Placeholders are typically NOT in z-order; ordinary text
        # shapes ARE.)
        for s in deck.slide[:20]:
            zo_set = set(s.drawables_z_order)
            for tb in s.texts:
                if tb._shape_id in zo_set:
                    before = s.z_index(tb)
                    assert before >= 0
                    assert s.bring_to_front(tb) is True
                    assert s.z_index(tb) == len(s.drawables_z_order) - 1
                    # And accept Image proxies too if any
                    for img in s.images:
                        if img._archive_id in zo_set:
                            s.send_to_back(img)
                            assert s.z_index(img) == 0
                            break
                    return
        pytest.skip("no z-ordered text blocks in first 20 slides")
    finally:
        deck.close()


# ============================================================
# Round-trip: z-order changes persist through save/open
# ============================================================


def test_zorder_round_trip(tmp_path):
    """Reorder shapes, save, reopen, verify the new order is on disk."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = list(s.drawables_z_order)
        target = original[0]
        assert s.bring_to_front(target) is True
        expected = original[1:] + [target]
        assert list(s.drawables_z_order) == expected
        out = tmp_path / "zorder_roundtrip.key"
        deck.save(out)
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        s2 = deck2.slide[0]
        assert list(s2.drawables_z_order) == expected
        print(f"\n  Round-trip: front shape now {s2.drawables_z_order[-1]} (was {original[0]})")
    finally:
        deck2.close()


def test_set_z_order_round_trip(tmp_path):
    """Full reorder persists through save/open."""
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        original = list(s.drawables_z_order)
        reversed_order = list(reversed(original))
        assert s.set_z_order(reversed_order) is True
        out = tmp_path / "zorder_reverse.key"
        deck.save(out)
    finally:
        deck.close()

    deck2 = kpa.Deck.from_template(out)
    try:
        s2 = deck2.slide[0]
        assert list(s2.drawables_z_order) == reversed_order
    finally:
        deck2.close()


# ============================================================
# Group proxy (read-only in 4c.3)
# ============================================================


def test_group_proxy_read_when_present():
    """Synthesize a fake group archive in-memory and verify the Group
    proxy reads it correctly. Real-deck round-trip is deferred until
    a sample with groups is added to recon/.
    """
    if not SVEF.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(SVEF)
    try:
        s = deck.slide[0]
        # Inject a fake KN.GroupArchive into the last chunk so the
        # groups property has something to find. We use two existing
        # drawable ids as the group's contents.
        zo_ids = s.drawables_z_order
        if len(zo_ids) < 2:
            pytest.skip("not enough drawables to fake a group")
        fake_id = "999000001"
        fake_archive = {
            "header": {
                "_pbtype": "TSP.ArchiveInfo",
                "identifier": fake_id,
                "messageInfos": [{"type": 14, "version": [1, 0, 5]}],
            },
            "objects": [
                {
                    "_pbtype": "KN.GroupArchive",
                    "contents": [
                        {"identifier": zo_ids[0]},
                        {"identifier": zo_ids[1]},
                    ],
                }
            ],
        }
        chunks = s._yaml_root.setdefault("chunks", [])
        if not chunks:
            chunks.append({"archives": []})
        chunks[-1].setdefault("archives", []).append(fake_archive)
        s._archive_index[fake_id] = fake_archive

        groups = s.groups
        assert len(groups) == 1
        g = groups[0]
        assert isinstance(g, Group)
        assert g.archive_id == fake_id
        assert g.children_ids == (zo_ids[0], zo_ids[1])
        # Escape hatch works on Group
        assert g.raw_pbtype() == "KN.GroupArchive"
        ck = g.raw_get("contents")
        assert isinstance(ck, list) and len(ck) == 2
        print(f"\n  Group proxy: id={g.archive_id} children={list(g.children_ids)}")
    finally:
        deck.close()
