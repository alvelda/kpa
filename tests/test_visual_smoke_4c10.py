"""
tests/test_visual_smoke_4c10.py
================================

Step 4c.10 \u2014 Visual smoke / golden-image testing.

The Keynote.app export driver lives in :mod:`kpa.visual_smoke`. These
unit tests cover the parts that don't need Keynote.app to run:

  - compare_images() pixel-diff logic (PIL-based)
  - tolerance threshold behavior (identical \u2192 0%, single-pixel diff
    well under default tolerance, large diff fails)
  - error reporting (missing file, size mismatch)
  - SmokeReport.passed aggregation

The AppleScript export driver (export_slides_as_png) requires a live
Keynote.app session with Automation permission granted and is skipped
in CI. Run ``pytest -m visual_smoke_live`` against a workstation with
Keynote installed to exercise it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from kpa.visual_smoke import (
    ImageDiff,
    SmokeReport,
    compare_images,
)


def _make_png(path: Path, size=(64, 64), color=(255, 255, 255)) -> Path:
    from PIL import Image
    Image.new("RGB", size, color).save(path)
    return path


def _make_png_with_dot(path: Path, size=(64, 64), color=(255, 255, 255), dot=(0, 0, 0)) -> Path:
    """A solid color image with a single dark pixel at (0, 0)."""
    from PIL import Image
    img = Image.new("RGB", size, color)
    img.putpixel((0, 0), dot)
    img.save(path)
    return path


# ============= image diff =============


def test_identical_images_match(tmp_path):
    a = _make_png(tmp_path / "a.png")
    b = _make_png(tmp_path / "b.png")
    diff = compare_images(a, b)
    assert diff.matches is True
    assert diff.pixel_diff_count == 0
    assert diff.pct_different == 0.0


def test_tiny_difference_within_tolerance(tmp_path):
    a = _make_png(tmp_path / "a.png", size=(100, 100))
    b = _make_png_with_dot(tmp_path / "b.png", size=(100, 100))
    diff = compare_images(a, b, tolerance_pct=0.005)
    # 1/10000 pixels different = 0.01%, under 0.5% default tolerance
    assert diff.matches is True
    assert diff.pixel_diff_count == 1
    assert diff.pixel_total == 10000
    assert diff.pct_different == 0.0001


def test_large_difference_fails(tmp_path):
    a = _make_png(tmp_path / "a.png", color=(255, 255, 255))
    b = _make_png(tmp_path / "b.png", color=(0, 0, 0))
    diff = compare_images(a, b)
    assert diff.matches is False
    assert diff.pct_different == 1.0


def test_size_mismatch_fails(tmp_path):
    a = _make_png(tmp_path / "a.png", size=(64, 64))
    b = _make_png(tmp_path / "b.png", size=(128, 128))
    diff = compare_images(a, b)
    assert diff.matches is False
    assert diff.error is not None
    assert "size mismatch" in diff.error


def test_missing_produced_file(tmp_path):
    b = _make_png(tmp_path / "b.png")
    diff = compare_images(tmp_path / "missing.png", b)
    assert diff.matches is False
    assert diff.error is not None
    assert "produced image missing" in diff.error


def test_missing_golden_file(tmp_path):
    a = _make_png(tmp_path / "a.png")
    diff = compare_images(a, tmp_path / "missing.png")
    assert diff.matches is False
    assert diff.error is not None
    assert "golden image missing" in diff.error


def test_tolerance_threshold_boundary(tmp_path):
    """A 1% pixel difference should fail at default 0.5% tolerance
    but pass at 2% tolerance."""
    from PIL import Image
    size = (100, 100)
    a = _make_png(tmp_path / "a.png", size=size)
    img = Image.new("RGB", size, (255, 255, 255))
    # Set 100 pixels (1%) to black
    for i in range(100):
        img.putpixel((i, 0), (0, 0, 0))
    img.save(tmp_path / "b.png")

    strict = compare_images(a, tmp_path / "b.png", tolerance_pct=0.005)
    assert strict.matches is False
    assert strict.pct_different == 0.01

    lenient = compare_images(a, tmp_path / "b.png", tolerance_pct=0.02)
    assert lenient.matches is True


# ============= SmokeReport aggregation =============


def test_report_passed_when_all_diffs_match(tmp_path):
    a = _make_png(tmp_path / "a.png")
    b = _make_png(tmp_path / "b.png")
    d1 = compare_images(a, b)
    d2 = compare_images(a, b)
    report = SmokeReport(deck=tmp_path / "x.key", diffs=[d1, d2])
    assert report.passed is True


def test_report_failed_when_any_diff_fails(tmp_path):
    a = _make_png(tmp_path / "a.png", color=(255, 255, 255))
    b = _make_png(tmp_path / "b.png", color=(255, 255, 255))
    c = _make_png(tmp_path / "c.png", color=(0, 0, 0))
    good = compare_images(a, b)
    bad = compare_images(a, c)
    report = SmokeReport(deck=tmp_path / "x.key", diffs=[good, bad])
    assert report.passed is False


def test_image_diff_summary_string(tmp_path):
    a = _make_png(tmp_path / "a.png")
    b = _make_png(tmp_path / "b.png")
    d = compare_images(a, b)
    assert "OK" in d.summary
    c = _make_png(tmp_path / "c.png", color=(0, 0, 0))
    d2 = compare_images(a, c)
    assert "FAIL" in d2.summary


def test_image_diff_summary_with_error(tmp_path):
    b = _make_png(tmp_path / "b.png")
    d = compare_images(tmp_path / "missing.png", b)
    assert "ERROR" in d.summary


# ============= Keynote export driver (skipped unless live) =============


@pytest.mark.skip(reason="requires live Keynote.app session; run manually with -p no:cacheprovider when ready")
def test_keynote_export_round_trip(tmp_path):
    """Live smoke: open recon/test1.key in Keynote.app, export PNGs,
    verify count matches deck slide count. Skipped in CI."""
    from kpa.visual_smoke import export_slides_as_png
    import kpa
    REPO = Path(__file__).resolve().parent.parent
    deck_path = REPO / "recon" / "test1.key"
    deck = kpa.Deck.from_template(deck_path)
    try:
        n_slides = len(deck.slide)
    finally:
        deck.close()
    out = tmp_path / "exported"
    pngs = export_slides_as_png(deck_path, out, timeout_s=180)
    assert len(pngs) == n_slides
