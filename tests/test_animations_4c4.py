"""
tests/test_animations_4c4.py
==============================

Step 4c.4 — Animations (KN.BuildArchive) + slide transitions round-trip.

Coverage:
  - Build.effect / animation_type / duration / delay / target / trigger /
    text_delivery / delivery_direction
  - Slide.add_build / remove_build (create + destroy)
  - Transition.effect / duration / delay / direction / is_automatic
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent


# =================== reads ===================


def test_read_transition_from_real_deck():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = deck.slide[0]
    t = s.transition
    assert t is not None
    print(f"\n  Slide 0 transition: {t}")
    # SVEF has apple:push transitions across the board
    assert t.effect == "apple:push"
    assert t.duration == pytest.approx(0.75)
    assert t.delay == pytest.approx(0.5)
    assert t.direction == 14
    deck.close()


def test_read_builds_from_real_deck():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    # Find any slide with builds
    found = False
    for i, s in enumerate(deck.slide):
        if s.builds:
            found = True
            b = s.builds[0]
            print(f"\n  Slide #{i} first build: {b}")
            assert b.effect is not None
            assert b.animation_type in ("In", "Out", "Action", "Content")
            assert b.duration is not None and b.duration > 0
            assert b.target_id is not None
            summary = b.summary()
            assert "archive_id" in summary
            break
    assert found, "Expected at least one slide with builds in SVEF"
    deck.close()


# =================== Build round-trips ===================


def _find_slide_with_build(deck):
    for s in deck.slide:
        if s.builds:
            return s
    return None


def test_build_effect_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    b = s.builds[0]
    orig = b.effect
    b.set_effect("fly_in")  # alias -> apple:fly-in
    out = tmp_path / "build_effect.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2)
    b2 = s2.builds[0]
    print(f"\n  effect: {orig!r} -> {b2.effect!r}")
    assert b2.effect == "apple:fly-in"
    deck2.close()


def test_build_duration_delay_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    b = s.builds[0]
    b.set_duration(2.5).set_delay(0.75)
    out = tmp_path / "build_timing.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2)
    b2 = s2.builds[0]
    print(f"\n  duration: -> {b2.duration} | delay: -> {b2.delay}")
    assert b2.duration == pytest.approx(2.5)
    assert b2.delay == pytest.approx(0.75)
    deck2.close()


def test_build_animation_type_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    b = s.builds[0]
    orig = b.animation_type
    b.set_animation_type("Out")
    out = tmp_path / "build_anim_type.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2)
    b2 = s2.builds[0]
    print(f"\n  animation_type: {orig} -> {b2.animation_type}")
    assert b2.animation_type == "Out"
    deck2.close()


def test_build_trigger_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    b = s.builds[0]
    orig = b.trigger_name
    b.set_trigger("with_previous")
    out = tmp_path / "build_trigger.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2)
    b2 = s2.builds[0]
    print(f"\n  trigger: {orig} -> {b2.trigger_name}")
    assert b2.trigger == 2  # WITH_PREVIOUS
    assert b2.trigger_name == "with_previous"
    deck2.close()


def test_build_text_delivery_round_trip(tmp_path):
    """4c.4: text_delivery and delivery_direction round-trip.

    Note: Only ``kTextDeliveryByObject`` is empirically observed in SVEF/NCI;
    other variants (paragraph/word/character) are in the proto schema but
    not present in our sample data. We test ``object`` (proven) here and
    leave the others as best-effort writes documented in the API.
    """
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    b = s.builds[0]
    b.set_text_delivery("object")
    b.set_delivery_direction("forward")
    out = tmp_path / "build_text.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2)
    b2 = s2.builds[0]
    print(f"\n  text_delivery: {b2.text_delivery_name} | direction: {b2.delivery_direction}")
    assert b2.text_delivery_name == "object"
    assert b2.delivery_direction == "forward"
    deck2.close()


# =================== add/remove ===================


def test_add_build_persists(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    # Pick a slide and a text block on it
    s = deck.slide[0]
    texts = s.texts
    assert texts, "Need a slide with at least one text block"
    target = texts[0]
    orig_count = len(s.builds)
    new_b = s.add_build(
        target,
        effect="fade",
        animation_type="In",
        duration=1.5,
        delay=0.25,
        trigger="after_previous",
    )
    assert new_b is not None
    assert new_b.effect == "apple:dissolve"  # 'fade' alias
    out = tmp_path / "add_build.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = deck2.slide[0]
    new_count = len(s2.builds)
    print(f"\n  builds count: {orig_count} -> {new_count}")
    assert new_count == orig_count + 1
    # Find the new build by its effect
    found = next((b for b in s2.builds if b.effect == "apple:dissolve"), None)
    assert found is not None
    assert found.duration == pytest.approx(1.5)
    assert found.delay == pytest.approx(0.25)
    assert found.trigger_name == "after_previous"
    deck2.close()


def test_remove_build_persists(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = _find_slide_with_build(deck)
    orig_count = len(s.builds)
    assert orig_count > 0
    victim = s.builds[0]
    assert s.remove_build(victim) is True
    out = tmp_path / "remove_build.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    s2 = _find_slide_with_build(deck2) if any(s.builds for s in deck2.slide) else deck2.slide[2]
    new_count = len(s2.builds)
    print(f"\n  builds count: {orig_count} -> {new_count}")
    assert new_count == orig_count - 1
    deck2.close()


# =================== Transition round-trips ===================


def test_transition_effect_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = deck.slide[0]
    t = s.transition
    orig = t.effect
    t.set_effect("magic_move")  # alias -> apple:magic move
    out = tmp_path / "trans_effect.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    t2 = deck2.slide[0].transition
    print(f"\n  transition effect: {orig!r} -> {t2.effect!r}")
    assert t2.effect == "apple:magic move"
    deck2.close()


def test_transition_duration_delay_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    t = deck.slide[0].transition
    t.set_duration(1.25).set_delay(0.1)
    out = tmp_path / "trans_timing.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    t2 = deck2.slide[0].transition
    print(f"\n  trans dur={t2.duration} delay={t2.delay}")
    assert t2.duration == pytest.approx(1.25)
    assert t2.delay == pytest.approx(0.1)
    deck2.close()


def test_transition_direction_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    t = deck.slide[0].transition
    orig = t.direction
    t.set_direction(7)  # arbitrary compass enum value
    out = tmp_path / "trans_dir.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    t2 = deck2.slide[0].transition
    print(f"\n  transition direction: {orig} -> {t2.direction}")
    assert t2.direction == 7
    deck2.close()


def test_transition_is_automatic_round_trip(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    t = deck.slide[0].transition
    orig = t.is_automatic
    t.set_automatic(True)
    out = tmp_path / "trans_auto.key"
    deck.save(out)
    deck.close()

    deck2 = kpa.Deck.from_template(out)
    t2 = deck2.slide[0].transition
    print(f"\n  transition is_automatic: {orig} -> {t2.is_automatic}")
    assert t2.is_automatic is True
    deck2.close()
