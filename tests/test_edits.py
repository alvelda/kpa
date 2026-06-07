"""
tests/test_edits.py
====================

Step 4b — F2b (surgical edits) gate.

What we test:
  - Load SVEF, set a text block's text, move it, save.
  - Re-open the saved deck and confirm the new text + new position
    survived the round-trip.
  - This is the foundation of every surgical-edit MCP call.

Note: we don't yet verify Keynote.app accepts the file (that's Step 4d
human review). The test only verifies that KPA's mutation -> save ->
load cycle is internally consistent. Step 4c will add the
brand-validator check on the saved file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent


def test_text_edit_and_move_round_trip(tmp_path):
    """F2b smoke: set_text + move land cleanly through save+reopen."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip(f"Reference deck {src} not available (local-only).")

    # Step 1: load and find a text block we can identify by content.
    deck = kpa.Deck.from_template(src)
    target = None
    for i, slide in enumerate(deck.slide):
        tb = slide.find_text("Appendix")
        if tb is not None:
            target = (i, slide.slide_id, tb.text, tb.position)
            tb.set_text("KPA TEST EDIT — Hello World")
            # move 50pt down and 25pt right
            tb.move(dx="+25pt", dy="+50pt")
            break

    assert target is not None, "Couldn't find a slide containing 'Appendix' in SVEF"
    orig_idx, orig_slide_id, orig_text, orig_pos = target
    print(f"\n  Edited slide #{orig_idx} (id={orig_slide_id}):")
    print(f"    text:     {orig_text!r} -> 'KPA TEST EDIT — Hello World'")
    print(f"    position: {orig_pos} -> +25pt right, +50pt down")

    # Step 2: save
    out_key = tmp_path / "edited.key"
    deck.save(out_key)
    deck.close()
    assert out_key.exists()

    # Step 3: re-open and verify edits persisted
    deck2 = kpa.Deck.from_template(out_key)
    found = None
    for i, slide in enumerate(deck2.slide):
        if slide.slide_id == orig_slide_id:
            tb = slide.find_text("KPA TEST EDIT")
            assert tb is not None, (
                f"On slide #{i} (id={orig_slide_id}), couldn't find the edited text."
            )
            found = (i, tb.text, tb.position)
            break
    assert found is not None, f"Edited slide id={orig_slide_id} missing from saved deck"
    new_idx, new_text, new_pos = found
    print(f"\n  After save+reload, slide #{new_idx}:")
    print(f"    text:     {new_text!r}")
    print(f"    position: {new_pos}")

    # Validate
    assert "KPA TEST EDIT" in new_text, f"Edited text didn't survive round-trip: {new_text!r}"
    expected_x = orig_pos[0] + 25.0
    expected_y = orig_pos[1] + 50.0
    assert abs(new_pos[0] - expected_x) < 0.01, (
        f"x didn't move correctly: {orig_pos[0]} + 25pt = {expected_x}, got {new_pos[0]}"
    )
    assert abs(new_pos[1] - expected_y) < 0.01, (
        f"y didn't move correctly: {orig_pos[1]} + 50pt = {expected_y}, got {new_pos[1]}"
    )
    deck2.close()


def test_set_position_with_percent(tmp_path):
    """F2b: pct-coordinate set_position lands at the expected pt values."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")

    deck = kpa.Deck.from_template(src)
    canvas = deck.canvas
    expected_x = 0.50 * canvas[0]  # 50% of 720 = 360
    expected_y = 0.25 * canvas[1]  # 25% of 405 = 101.25

    target_slide_id = None
    for i, slide in enumerate(deck.slide):
        tb = slide.find_text("Appendix")
        if tb is not None:
            tb.set_position("50%", "25%")
            target_slide_id = slide.slide_id
            break
    assert target_slide_id is not None

    out_key = tmp_path / "moved.key"
    deck.save(out_key)
    deck.close()

    deck2 = kpa.Deck.from_template(out_key)
    for slide in deck2.slide:
        if slide.slide_id == target_slide_id:
            tb = slide.find_text("Appendix")
            assert tb is not None
            print(f"\n  Expected: ({expected_x}, {expected_y})")
            print(f"  Got:      {tb.position}")
            assert abs(tb.position[0] - expected_x) < 0.01
            assert abs(tb.position[1] - expected_y) < 0.01
            break
    deck2.close()


def test_image_move(tmp_path):
    """F2b: image position mutation round-trips."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")

    deck = kpa.Deck.from_template(src)
    target_slide_id = None
    orig_pos = None
    for i, slide in enumerate(deck.slide):
        if slide.images:
            img = slide.images[0]
            if img.position is None:
                continue
            target_slide_id = slide.slide_id
            orig_pos = img.position
            img.move(dx="+10pt", dy="-15pt")
            break
    assert target_slide_id is not None, "No slide had an image with geometry"

    out_key = tmp_path / "moved-img.key"
    deck.save(out_key)
    deck.close()

    deck2 = kpa.Deck.from_template(out_key)
    for slide in deck2.slide:
        if slide.slide_id == target_slide_id:
            img = slide.images[0]
            print(f"\n  Image original: {orig_pos}")
            print(f"  Image after:    {img.position}")
            assert abs(img.position[0] - (orig_pos[0] + 10)) < 0.01
            assert abs(img.position[1] - (orig_pos[1] - 15)) < 0.01
            break
    deck2.close()
