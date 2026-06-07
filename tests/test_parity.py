"""
tests/test_parity.py
=====================

Step 4a — S4.1 gate.

The "no-op mutation" parity invariant: loading an existing ``.key``
via ``kpa.Deck.from_template(...)`` and saving it back out must
produce a file whose unpacked content is byte-identical (structural)
to the source's unpacked content.

This is the foundation under all of Step 4. If the round-trip can't
preserve bytes when nothing changed, no mutation can be trusted.

Reference decks:
  * recon/svef.key — 628 inner files byte-identical baseline
  * recon/nci.key  — 325 inner files byte-identical baseline (post-Bug-#5 fix)
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import kpa


REPO = Path(__file__).resolve().parent.parent


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def structural_diff(src_dir: Path, dst_dir: Path) -> tuple[int, int, list[str]]:
    """Compute identical/different counts between two unpacked-deck trees.

    Returns (identical, total_common, differing_paths_first10).
    """
    src_files = sorted(p.relative_to(src_dir) for p in src_dir.rglob("*") if p.is_file())
    dst_files = sorted(p.relative_to(dst_dir) for p in dst_dir.rglob("*") if p.is_file())
    src_set, dst_set = set(src_files), set(dst_files)
    common = sorted(src_set & dst_set)

    only_src = sorted(src_set - dst_set)
    only_dst = sorted(dst_set - src_set)
    diffs: list[str] = []
    if only_src:
        diffs.append(f"<only-in-src> {[str(p) for p in only_src[:5]]}")
    if only_dst:
        diffs.append(f"<only-in-dst> {[str(p) for p in only_dst[:5]]}")

    identical = 0
    for f in common:
        if sha256_file(src_dir / f) == sha256_file(dst_dir / f):
            identical += 1
        else:
            if len(diffs) < 10:
                sp, dp = src_dir / f, dst_dir / f
                diffs.append(
                    f"{f}: {sp.stat().st_size}B vs {dp.stat().st_size}B"
                )
    return identical, len(common), diffs


@pytest.mark.parametrize("deck_file,expected_count", [
    ("recon/svef.key", 628),
    ("recon/nci.key", 325),
])
def test_no_op_parity(tmp_path, deck_file, expected_count):
    """S4.1 — load + save = byte-identical structural round-trip.

    Tests the foundation: every IWA file, every Data asset, every
    Metadata entry should survive the load/save cycle unchanged.
    """
    src = REPO / deck_file
    if not src.exists():
        pytest.skip(f"Reference deck {src} not in repo (local-only).")

    # 1) Load via KPA
    deck = kpa.Deck.from_template(src)

    # 2) Save via KPA
    out_key = tmp_path / "roundtrip.key"
    deck.save(out_key)
    assert out_key.exists(), f"KPA did not write {out_key}"

    # 3) Re-unpack both via keynote-parser CLI (the truth)
    src_unpack = tmp_path / "src-unpack"
    dst_unpack = tmp_path / "dst-unpack"

    for keypath, outdir in [(src, src_unpack), (out_key, dst_unpack)]:
        r = subprocess.run(
            ["keynote-parser", "unpack", str(keypath), "--output", str(outdir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, (
            f"keynote-parser unpack failed for {keypath}: {r.stderr[-500:]}"
        )

    # 4) Structural sha256 diff
    identical, total, diffs = structural_diff(src_unpack, dst_unpack)
    print(f"\n  identical: {identical}/{total} (expected {expected_count})")
    if diffs:
        print("  diffs (first 10):")
        for d in diffs:
            print(f"    {d}")

    assert total == expected_count, (
        f"Expected {expected_count} common files, got {total} "
        f"(src={len(list(src_unpack.rglob('*')))}, dst={len(list(dst_unpack.rglob('*')))})"
    )
    assert identical == total, (
        f"S4.1 parity FAILED: {identical}/{total} byte-identical; "
        f"first diffs: {diffs[:5]}"
    )

    deck.close()


def test_deck_summary():
    """Smoke: Deck.summary() returns a readable string for SVEF."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    s = deck.summary()
    assert "slides:" in s
    assert "data assets:" in s
    print("\n  " + s.replace("\n", "\n  "))
    deck.close()
