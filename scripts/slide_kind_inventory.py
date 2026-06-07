#!/usr/bin/env python3
"""
scripts/slide_kind_inventory.py
================================

Inventory the distinct slide kinds present in SVEF and NCI.

KPA Step 4a deliverable (Captain Q3): the slide-kind taxonomy is a
growing library; we seed it from the kinds actually observed in the
reference decks rather than guessing.

For each slide in `recon/unpacked/{svef,nci}/Index/Slide-*.iwa.yaml`,
extract:
  - master slide reference (if any) — proxies for "kind"
  - placeholder roles found in the slide's text/image children
  - structural fingerprint: counts of (text, image, group, shape, chart, table)
  - cluster slides by master + structural fingerprint

Emit:
  - `docs/SLIDE_KINDS.md` — human-readable summary of observed kinds
  - `docs/SLIDE_KINDS.json` — machine-readable inventory for the
    `kpa.slide_kinds` library bootstrap

Usage:
    python3 scripts/slide_kind_inventory.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


REPO = Path(__file__).resolve().parent.parent


def load_slide(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def walk_objects(data: Any):
    """Yield every dict-shaped object in the YAML tree."""
    if isinstance(data, dict):
        yield data
        for v in data.values():
            yield from walk_objects(v)
    elif isinstance(data, list):
        for item in data:
            yield from walk_objects(item)


def fingerprint(slide_yaml: dict[str, Any]) -> dict[str, Any]:
    """Extract a structural fingerprint for the slide.

    Slides have the shape:
      KN.SlideArchive {
        templateSlide: { identifier: ... }       # master ref
        titlePlaceholder: { identifier: ... }    # slot pointers
        bodyPlaceholder: { identifier: ... }
        slideNumberPlaceholder: { identifier: ... }
        ownedDrawables: [ { identifier: ... }, ... ]  # visual content
      }
      + child KN.PlaceholderArchive entries with `kind` enum string
      + child TSD.* (image, shape, group, mask) and TSWP.* (text)
      + child TSCH.* (chart) and TST.* (table)
    """
    obj_count: Counter[str] = Counter()
    placeholder_kinds: list[str] = []
    template_slide_ref = None
    title_placeholder_ref = None
    body_placeholder_ref = None
    slide_archive_keys = []
    n_owned_drawables = 0

    for obj in walk_objects(slide_yaml):
        pbtype = obj.get("_pbtype")
        if pbtype:
            obj_count[pbtype] += 1
            if pbtype == "KN.SlideArchive":
                slide_archive_keys = sorted(set(obj.keys()) - {"_pbtype"})
                ts = obj.get("templateSlide")
                if isinstance(ts, dict) and "identifier" in ts:
                    template_slide_ref = str(ts["identifier"])
                tp = obj.get("titlePlaceholder")
                if isinstance(tp, dict) and "identifier" in tp:
                    title_placeholder_ref = str(tp["identifier"])
                bp = obj.get("bodyPlaceholder")
                if isinstance(bp, dict) and "identifier" in bp:
                    body_placeholder_ref = str(bp["identifier"])
                od = obj.get("ownedDrawables")
                if isinstance(od, list):
                    n_owned_drawables = len(od)
            if pbtype == "KN.PlaceholderArchive":
                kind = obj.get("kind")
                if kind is not None:
                    placeholder_kinds.append(str(kind))

    # Some image archives are decorative (background) vs content; we count
    # all of them but track separately whether the slide has *visible*
    # placeholders besides title/body/slideNumber.
    return {
        "objects_by_type": dict(obj_count),
        "template_slide_ref": template_slide_ref,
        "title_placeholder_ref": title_placeholder_ref,
        "body_placeholder_ref": body_placeholder_ref,
        "placeholder_kinds": placeholder_kinds,
        "n_owned_drawables": n_owned_drawables,
        "slide_archive_keys": slide_archive_keys,
        "has_title_slot": title_placeholder_ref is not None,
        "has_body_slot": body_placeholder_ref is not None,
        "n_text_storages": obj_count.get("TSWP.StorageArchive", 0),
        "n_image_archives": (
            obj_count.get("TSD.ImageArchive", 0)
            + obj_count.get("TSD.MediaArchive", 0)
            + obj_count.get("TSD.MovieArchive", 0)
        ),
        "n_shape_archives": obj_count.get("TSD.ShapeArchive", 0),
        "n_group_archives": obj_count.get("TSD.GroupArchive", 0),
        "n_chart_archives": (
            obj_count.get("TSCH.ChartArchive", 0)
            + obj_count.get("TSCH.ChartGridArchive", 0)
        ),
        "n_table_archives": obj_count.get("TST.TableInfoArchive", 0),
        "n_shape_infos": obj_count.get("TSWP.ShapeInfoArchive", 0),
        "n_mask_archives": obj_count.get("TSD.MaskArchive", 0),
    }


def kind_label(fp: dict[str, Any]) -> str:
    """Derive a coarse slide kind label from the fingerprint.

    We use the actual placeholder kinds + content counts. Placeholder
    kind enums observed in SVEF/NCI:
      kKindTitle
      kKindBody
      kKindObject (generic content slot)
      kKindSlideNumberPlaceholder
      kKindBulletsBody / kKindUnorderedList
      kKindCenteredTitle / kKindSubtitle
      kKindImage
      kKindChart, kKindTable
    Plus content counts (n_image, n_chart, n_text_storages, n_owned_drawables).
    """
    n_text = fp["n_text_storages"]
    n_image = fp["n_image_archives"]
    n_chart = fp["n_chart_archives"]
    n_table = fp["n_table_archives"]
    n_shape = fp["n_shape_archives"]
    n_drawables = fp["n_owned_drawables"]
    has_title = fp["has_title_slot"]
    has_body = fp["has_body_slot"]
    p_kinds = set(fp["placeholder_kinds"])

    # Strongest signals first
    if n_chart >= 1:
        return "chart"
    if n_table >= 1:
        return "table"

    # Pure title slide: title + maybe subtitle, no body, no images, few drawables
    title_like_placeholders = {
        "kKindTitle", "kKindCenteredTitle", "kKindSubtitle"
    }
    if p_kinds & title_like_placeholders and not has_body and n_image == 0 and n_drawables <= 4:
        return "title"

    # Section divider: title, no body slot, very few drawables
    if has_title and not has_body and n_image == 0 and n_drawables <= 3:
        return "section_divider"

    # Image + text: at least one image + a text-bearing placeholder
    if n_image >= 1 and (has_title or has_body or n_text >= 2):
        return "text_image"

    # Quote: has body but only 1–2 text storages, no image
    if has_body and n_image == 0 and n_text <= 3 and n_drawables <= 4:
        return "quote"

    # Bullet list: has body, has multiple text shapes, no image
    if has_body and n_image == 0 and (n_text >= 3 or fp["n_shape_infos"] >= 2):
        return "bullet_list"

    # Image-only
    if n_image >= 1 and not has_title and not has_body:
        return "image_only"

    # Mostly visual / decorative
    if n_image >= 2 and n_text <= 1:
        return "image_heavy"

    # Text-only catchall
    if n_text >= 1:
        return "text_only"

    # Closing slide is hard to detect structurally without semantic clues;
    # for now bucket short title-only slides as "closing_candidate"
    if has_title and n_drawables <= 2 and n_text <= 1:
        return "closing_candidate"

    return "unknown"


def inventory_deck(name: str, path: Path) -> dict[str, Any]:
    slide_files = sorted(path.glob("Slide-*.iwa.yaml"))
    print(f"  {name}: scanning {len(slide_files)} slide YAMLs...")
    by_kind: dict[str, list[str]] = defaultdict(list)
    by_master: dict[str, list[str]] = defaultdict(list)
    placeholder_kind_counter: Counter[str] = Counter()
    fps: dict[str, dict[str, Any]] = {}

    for sf in slide_files:
        try:
            data = load_slide(sf)
        except yaml.YAMLError as e:
            print(f"  WARN: failed to parse {sf.name}: {e}", file=sys.stderr)
            continue
        fp = fingerprint(data)
        kind = kind_label(fp)
        slide_id = sf.stem.replace(".iwa", "")
        by_kind[kind].append(slide_id)
        if fp["template_slide_ref"]:
            by_master[fp["template_slide_ref"]].append(slide_id)
        for pk in fp["placeholder_kinds"]:
            placeholder_kind_counter[pk] += 1
        fps[slide_id] = fp

    return {
        "deck": name,
        "n_slides": len(slide_files),
        "by_kind": {k: sorted(v) for k, v in sorted(by_kind.items())},
        "by_master_ref": {
            k: sorted(v) for k, v in sorted(by_master.items(), key=lambda x: -len(x[1]))
        },
        "placeholder_kinds": dict(placeholder_kind_counter.most_common()),
        "fingerprints": fps,
    }


def main():
    decks = {
        "svef": REPO / "recon" / "unpacked" / "svef" / "Index",
        "nci": REPO / "recon" / "unpacked" / "nci" / "Index",
    }
    print("=== KPA Slide-Kind Inventory ===")
    results = {}
    for name, path in decks.items():
        if not path.exists():
            print(f"  {name}: {path} missing, skipping")
            continue
        results[name] = inventory_deck(name, path)

    # Cross-deck summary
    all_kinds: Counter[str] = Counter()
    for d in results.values():
        for k, v in d["by_kind"].items():
            all_kinds[k] += len(v)

    out_dir = REPO / "docs"
    out_dir.mkdir(exist_ok=True)
    json_out = out_dir / "SLIDE_KINDS.json"
    md_out = out_dir / "SLIDE_KINDS.md"

    # Trim fingerprints to keep JSON small but preserve per-slide structure
    slim = {}
    for name, d in results.items():
        slim[name] = {
            "n_slides": d["n_slides"],
            "by_kind_counts": {k: len(v) for k, v in d["by_kind"].items()},
            "by_kind": d["by_kind"],
            "by_master_ref_top10": {k: v[:5] + ([f"... +{len(v)-5} more"] if len(v) > 5 else []) for k, v in list(d["by_master_ref"].items())[:10]},
            "placeholder_kinds_observed": d["placeholder_kinds"],
        }
    slim["combined_kind_counts"] = dict(all_kinds.most_common())

    with open(json_out, "w") as f:
        json.dump(slim, f, indent=2)
    print(f"\nWrote {json_out}")

    lines = ["# Slide-Kind Inventory — SVEF + NCI",
             "",
             "**Generated:** by `scripts/slide_kind_inventory.py`",
             "**Step:** 4a (Captain Q3 — slide-kind taxonomy seeded from reference decks)",
             "",
             "## Combined kind counts",
             "",
             "| Kind | Slides across both decks |",
             "|---|---|"]
    for k, c in all_kinds.most_common():
        lines.append(f"| `{k}` | {c} |")
    lines.append("")
    for name, d in results.items():
        lines.append(f"## {name.upper()} ({d['n_slides']} slides)")
        lines.append("")
        lines.append("### Slides by kind")
        lines.append("")
        lines.append("| Kind | Count |")
        lines.append("|---|---|")
        for k, v in sorted(d["by_kind"].items(), key=lambda kv: -len(kv[1])):
            lines.append(f"| `{k}` | {len(v)} |")
        lines.append("")
        lines.append("### Top template-slide (master) references")
        lines.append("")
        lines.append("| Template ID | # slides using it |")
        lines.append("|---|---|")
        for m, sl in list(d["by_master_ref"].items())[:10]:
            lines.append(f"| `{m}` | {len(sl)} |")
        lines.append("")
        lines.append("### Placeholder kinds observed")
        lines.append("")
        lines.append("| Placeholder kind enum | Count |")
        lines.append("|---|---|")
        for pk, c in list(d["placeholder_kinds"].items())[:25]:
            lines.append(f"| `{pk}` | {c} |")
        lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "The kind labels above are heuristic, derived from structural "
        "fingerprints (counts of text/image/chart/table/shape archives + "
        "title/body/byline placeholder hints). The final `kpa.slide_kinds` "
        "library will use these as seeds and add semantic role tags "
        "(`title`, `text_image`, `bullet_list`, `quote`, `closing`, "
        "`section_divider`, `chart`, `table`, `image_only`, `text_only`) "
        "during Step 4b/4c as we author against them."
    )
    lines.append("")
    lines.append(
        "Master-slide references show which template slides each deck reuses "
        "most heavily — those are the high-value cloning targets for the "
        "template-anchored authoring flow in Step 4b."
    )
    lines.append("")

    with open(md_out, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {md_out}")
    print()
    print("=== Combined kind counts ===")
    for k, c in all_kinds.most_common():
        print(f"  {k:<25s} {c}")


if __name__ == "__main__":
    main()
