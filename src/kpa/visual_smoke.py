"""
src/kpa/visual_smoke.py
==========================

Visual smoke / golden-image testing for KPA-edited Keynote decks.

Round-trip tests verify that the *archive structure* survives a save and
reopen. They don't catch the failure modes where the file is structurally
valid but Keynote renders it wrong (z-order regressions, broken style
refs, missing geometry, dropped placeholders).

This module drives Keynote.app via AppleScript to:
  1. Open a .key file
  2. Export every slide as PNG (or a specified slide range)
  3. Close the document without saving

You can then diff the produced PNG against a golden image to detect
rendering regressions.

Public API:

    export_slides_as_png(deck_path, output_dir, slides=None) -> list[Path]
    compare_images(produced_path, golden_path) -> ImageDiff
    smoke_test(deck_path, golden_dir, slides=None) -> SmokeReport

Constraints:

  - Requires macOS with Keynote.app installed.
  - Keynote.app must have permission to be controlled via AppleScript
    (System Settings → Privacy & Security → Automation).
  - Each export takes ~5-20 seconds because Keynote has to launch and
    render. This is NOT a test you run on every commit \u2014 it's a
    nightly/release smoke gate.
  - The image comparison is pixel-based with a configurable tolerance
    (default: 0.5% of pixels can differ). Anti-aliasing on text means
    exact pixel matches are unreliable.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ImageDiff:
    """Result of comparing two images."""
    produced: Path
    golden: Path
    matches: bool
    pixel_diff_count: int = 0
    pixel_total: int = 0
    pct_different: float = 0.0
    error: Optional[str] = None

    @property
    def summary(self) -> str:
        if self.error:
            return f"ERROR: {self.error}"
        if self.matches:
            return f"OK ({self.pct_different:.3%} pixel diff)"
        return (
            f"FAIL ({self.pixel_diff_count}/{self.pixel_total} pixels "
            f"differ, {self.pct_different:.3%})"
        )


@dataclass
class SmokeReport:
    """Result of a visual smoke run across one or more slides."""
    deck: Path
    diffs: list[ImageDiff] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(d.matches for d in self.diffs)


# ---------------------------- AppleScript helpers ----------------------------


_EXPORT_SCRIPT = """
on run argv
    set deckPath to item 1 of argv
    set outDir to item 2 of argv
    set deckAlias to POSIX file deckPath
    set outAlias to POSIX file outDir
    tell application id "com.apple.iWork.Keynote"
        activate
        set theDoc to open deckAlias
        set exportProps to {image format:PNG, export style:IndividualSlides}
        export theDoc to outAlias as slide images with properties exportProps
        close theDoc saving no
    end tell
end run
"""


def _keynote_available() -> bool:
    return Path("/Applications/Keynote.app").exists()


def export_slides_as_png(
    deck_path: Path, output_dir: Path, timeout_s: int = 120
) -> list[Path]:
    """Drive Keynote.app to export every slide of ``deck_path`` as PNG.

    Returns the sorted list of PNG paths in ``output_dir``.

    Raises:
        RuntimeError if Keynote.app is missing, AppleScript fails, or
        the timeout fires.
    """
    if not _keynote_available():
        raise RuntimeError("Keynote.app not installed at /Applications/Keynote.app")
    deck_path = Path(deck_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not deck_path.exists():
        raise FileNotFoundError(deck_path)

    # Drop the AppleScript into a temp file (the run-time osascript -e
    # quoting is finicky with multiline scripts).
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".applescript", delete=False
    ) as fh:
        fh.write(_EXPORT_SCRIPT)
        script_path = Path(fh.name)
    try:
        result = subprocess.run(
            [
                "osascript", str(script_path),
                str(deck_path),
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"osascript failed (rc={result.returncode}): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
    finally:
        script_path.unlink(missing_ok=True)
    pngs = sorted(output_dir.rglob("*.png"))
    if not pngs:
        raise RuntimeError(
            f"Keynote export produced no PNGs in {output_dir}; "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return pngs


# ---------------------------- image comparison ----------------------------


def compare_images(
    produced_path: Path, golden_path: Path, tolerance_pct: float = 0.005
) -> ImageDiff:
    """Compare two PNG files pixel-wise. Returns an :class:`ImageDiff`.

    The comparison tolerates ``tolerance_pct`` fraction of pixels
    differing (default 0.5%) to absorb anti-aliasing noise. A pixel is
    considered "different" if any RGB channel deviates by more than 5
    (out of 255).
    """
    from PIL import Image, ImageChops

    produced_path = Path(produced_path)
    golden_path = Path(golden_path)
    if not produced_path.exists():
        return ImageDiff(
            produced=produced_path,
            golden=golden_path,
            matches=False,
            error=f"produced image missing: {produced_path}",
        )
    if not golden_path.exists():
        return ImageDiff(
            produced=produced_path,
            golden=golden_path,
            matches=False,
            error=f"golden image missing: {golden_path}",
        )

    try:
        a = Image.open(produced_path).convert("RGB")
        b = Image.open(golden_path).convert("RGB")
    except Exception as e:
        return ImageDiff(
            produced=produced_path,
            golden=golden_path,
            matches=False,
            error=f"failed to load images: {e}",
        )
    if a.size != b.size:
        return ImageDiff(
            produced=produced_path,
            golden=golden_path,
            matches=False,
            error=f"size mismatch: produced={a.size} golden={b.size}",
        )
    diff = ImageChops.difference(a, b)
    bbox = diff.getbbox()
    total = a.size[0] * a.size[1]
    if bbox is None:
        return ImageDiff(
            produced=produced_path,
            golden=golden_path,
            matches=True,
            pixel_diff_count=0,
            pixel_total=total,
            pct_different=0.0,
        )
    # Count pixels where any channel deviates by more than the threshold.
    threshold = 5
    diff_bytes = diff.tobytes()
    n_diff = 0
    for i in range(0, len(diff_bytes), 3):
        r, g, b_ = diff_bytes[i], diff_bytes[i + 1], diff_bytes[i + 2]
        if r > threshold or g > threshold or b_ > threshold:
            n_diff += 1
    pct = n_diff / total
    return ImageDiff(
        produced=produced_path,
        golden=golden_path,
        matches=pct <= tolerance_pct,
        pixel_diff_count=n_diff,
        pixel_total=total,
        pct_different=pct,
    )


# ---------------------------- end-to-end smoke ----------------------------


def smoke_test(
    deck_path: Path,
    golden_dir: Path,
    tolerance_pct: float = 0.005,
    slides: Optional[list[int]] = None,
    keep_produced: bool = False,
) -> SmokeReport:
    """Export ``deck_path`` via Keynote.app and diff every produced PNG
    against a corresponding golden in ``golden_dir``.

    Golden naming convention: ``<deck_stem>.<index>.png``, where index is
    1-based to match Keynote's export naming. Missing goldens are
    flagged in the per-slide diff and cause ``report.passed`` to be False.

    Set ``keep_produced=True`` to retain the exported PNGs (e.g. so you
    can copy them in as new goldens on first run); otherwise the produced
    dir is temporary.
    """
    deck_path = Path(deck_path).resolve()
    golden_dir = Path(golden_dir).resolve()
    out_dir = Path(tempfile.mkdtemp(prefix="kpa_smoke_"))
    try:
        produced = export_slides_as_png(deck_path, out_dir)
        # Keynote names files like "<deck>.001.png", "<deck>.002.png", ...
        report = SmokeReport(deck=deck_path)
        for i, png in enumerate(produced, start=1):
            if slides is not None and i not in slides:
                continue
            golden = golden_dir / f"{deck_path.stem}.{i:03d}.png"
            diff = compare_images(png, golden, tolerance_pct=tolerance_pct)
            report.diffs.append(diff)
        if keep_produced:
            # Move into golden_dir-like sibling for inspection.
            stash = golden_dir.parent / f"{deck_path.stem}_produced"
            stash.mkdir(parents=True, exist_ok=True)
            for png in produced:
                shutil.copy2(png, stash / png.name)
        return report
    finally:
        if not keep_produced:
            shutil.rmtree(out_dir, ignore_errors=True)
