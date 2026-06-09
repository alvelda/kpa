"""
tests/test_phase1_close_4c8.py
================================

Step 4c.8 — Phase 1 closer. Three deliverables in one sub-step:

  1. Slide-kind library  (kpa.slide_kinds)
  2. Asset grovel        (kpa.assets)
  3. Brand validator     (kpa.validator)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import kpa
from kpa.slide_kinds import (
    SlideKind,
    list_slide_kinds,
    find_slide_kind,
    slide_kind_for_slide,
)
from kpa.assets import (
    Asset,
    list_assets,
    asset_summary,
    extract_all_assets,
)
from kpa.validator import (
    Brand,
    Rule,
    Violation,
    ValidationReport,
    MinSlideCount,
    MaxSlideCount,
    ForbidFontFamilies,
    RequireFontInBodyText,
    RequireStyleNamePresent,
    available_rules,
)


REPO = Path(__file__).resolve().parent.parent


# =================== 1. Slide-kind library ===================


def test_list_slide_kinds_in_svef():
    """SVEF ships 27 template slides (the slide-kind library for its
    theme). Each carries a canonical name."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    kinds = list_slide_kinds(deck)
    assert len(kinds) >= 25, f"Expected ~27 template slides; got {len(kinds)}"
    assert all(isinstance(k, SlideKind) for k in kinds)
    names = [k.name for k in kinds if k.name]
    print(f"\n  Found {len(kinds)} slide kinds; first 5 names:")
    for n in names[:5]:
        print(f"    - {n!r}")
    deck.close()


def test_slide_kind_known_names_present():
    """SVEF (theme 'Amadeus' or similar) should expose at least the
    canonical Apple kinds: BLANK, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS.
    """
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    names_upper = {(k.name or "").upper() for k in list_slide_kinds(deck)}
    must = {"BLANK", "TITLE_AND_BODY", "TITLE_AND_TWO_COLUMNS"}
    missing = must - names_upper
    assert not missing, f"Missing canonical kinds: {missing}"
    print(f"\n  Confirmed presence of: {sorted(must)}")
    deck.close()


def test_find_slide_kind_by_name():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    # case-insensitive
    sk = find_slide_kind(deck, name="title_and_body")
    assert sk is not None
    assert (sk.name or "").upper() == "TITLE_AND_BODY"
    print(f"\n  find by name -> {sk!r}")
    deck.close()


def test_find_slide_kind_by_identifier():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    first = list_slide_kinds(deck)[0]
    found = find_slide_kind(deck, identifier=first.identifier)
    assert found is not None
    assert found.identifier == first.identifier
    print(f"\n  find by id -> {found!r}")
    deck.close()


def test_find_slide_kind_misses_return_none():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    assert find_slide_kind(deck, name="NO_SUCH_KIND") is None
    assert find_slide_kind(deck, identifier="9999999") is None
    deck.close()


def test_slide_kind_placeholder_introspection():
    """Every TITLE_AND_BODY template should have title + body
    placeholders defined."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sk = find_slide_kind(deck, name="TITLE_AND_BODY")
    assert sk is not None
    assert sk.has_title_placeholder
    assert sk.has_body_placeholder
    assert isinstance(sk.drawable_count, int)
    print(f"\n  {sk!r}: title={sk.has_title_placeholder}, "
          f"body={sk.has_body_placeholder}, "
          f"drawables={sk.drawable_count}")
    deck.close()


def test_slide_kind_for_slide_resolves_template():
    """Every real slide references a template via templateSlide.
    slide_kind_for_slide should resolve that to a SlideKind proxy."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    matched = 0
    for s in deck.slide[:10]:
        sk = slide_kind_for_slide(s)
        if sk is not None:
            matched += 1
    assert matched > 0, "No slide resolved to a template kind"
    print(f"\n  {matched}/{min(10, len(deck.slide))} slides resolved to a template")
    deck.close()


def test_slide_kind_raw_archive_access():
    """SlideKind inherits RawArchiveMixin (read-only first pass)."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    sk = find_slide_kind(deck, name="BLANK")
    assert sk is not None
    assert sk.raw_pbtype() == "KN.SlideArchive"
    keys = sk.raw_keys()
    assert "name" in keys
    assert sk.raw_get("name") == "BLANK"
    print(f"\n  raw_pbtype={sk.raw_pbtype()}, raw_get('name')={sk.raw_get('name')!r}")
    deck.close()


# =================== 2. Asset grovel ===================


def test_list_assets_in_svef():
    """SVEF ships several hundred embedded assets in Data/."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    assets = list_assets(deck)
    assert len(assets) > 100, f"Expected SVEF to have many assets; got {len(assets)}"
    assert all(isinstance(a, Asset) for a in assets)
    print(f"\n  SVEF has {len(assets)} assets")
    deck.close()


def test_list_assets_kind_filter():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    images = list_assets(deck, kind="image")
    videos = list_assets(deck, kind="video")
    assert len(images) > 0, "Expected some images"
    assert len(videos) >= 1, "SVEF has at least one mp4"
    assert all(a.kind == "image" for a in images)
    assert all(a.kind == "video" for a in videos)
    print(f"\n  images: {len(images)}, videos: {len(videos)}")
    deck.close()


def test_asset_kind_classification():
    """Spot-check classification across known extensions."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    assets = list_assets(deck)
    kinds = {a.extension: a.kind for a in assets}
    # SVEF has png/jpeg/jpg/tiff (image), mp4 (video), pdf (document)
    if ".png" in kinds: assert kinds[".png"] == "image"
    if ".jpeg" in kinds: assert kinds[".jpeg"] == "image"
    if ".jpg" in kinds: assert kinds[".jpg"] == "image"
    if ".mp4" in kinds: assert kinds[".mp4"] == "video"
    if ".pdf" in kinds: assert kinds[".pdf"] == "document"
    print(f"\n  Classified extensions: {sorted(kinds.keys())}")
    deck.close()


def test_asset_summary_bucket_totals():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    summ = asset_summary(deck)
    assert "total" in summ
    assert summ["total"]["count"] > 0
    assert summ["total"]["bytes"] > 0
    # Buckets sum to total
    bucket_count = sum(v["count"] for k, v in summ.items() if k != "total")
    bucket_bytes = sum(v["bytes"] for k, v in summ.items() if k != "total")
    assert bucket_count == summ["total"]["count"]
    assert bucket_bytes == summ["total"]["bytes"]
    print(f"\n  Asset summary: total={summ['total']['count']} files, "
          f"{summ['total']['bytes']/1024:.0f}KB")
    for k, v in summ.items():
        if k == "total": continue
        print(f"    {k}: {v['count']} files, {v['bytes']/1024:.0f}KB")
    deck.close()


def test_extract_single_asset(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    assets = list_assets(deck)
    first = assets[0]
    out = first.extract_to(tmp_path / "out")
    assert out.exists()
    assert out.stat().st_size == first.size_bytes
    assert out.name == first.filename
    print(f"\n  Extracted {first.filename} ({first.size_bytes} bytes) to {out}")
    deck.close()


def test_extract_all_assets_image_only(tmp_path):
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    out_dir = tmp_path / "images"
    paths = extract_all_assets(deck, out_dir, kind="image")
    assert len(paths) > 0
    assert all(p.exists() for p in paths)
    assert all(p.parent == out_dir for p in paths)
    # All extracted files should classify as image extensions
    image_exts = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".gif",
                  ".webp", ".avif", ".heic", ".heif", ".bmp", ".svg"}
    for p in paths:
        assert p.suffix.lower() in image_exts, p
    print(f"\n  Extracted {len(paths)} images to {out_dir}")
    deck.close()


# =================== 3. Brand validator ===================


def test_min_slide_count_passes_for_real_deck():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    brand = Brand(name="Test", rules=[MinSlideCount(n=1)])
    report = brand.validate(deck)
    assert report.ok
    assert report.error_count == 0
    print(f"\n  {report.summary()}")
    deck.close()


def test_min_slide_count_fails_on_small_deck():
    """A rule that requires more slides than the deck has should fire."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    huge_min = len(deck.slide) + 10
    brand = Brand(name="Test", rules=[MinSlideCount(n=huge_min)])
    report = brand.validate(deck)
    assert not report.ok
    assert report.error_count == 1
    assert "minimum is" in report.violations[0].message
    print(f"\n  Triggered MinSlideCount: {report.violations[0]}")
    deck.close()


def test_max_slide_count_warns_not_errors():
    """MaxSlideCount fires as a warning, not an error — exceeding the
    recommended cap shouldn't block, just flag."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    tiny_max = max(1, len(deck.slide) - 5)
    brand = Brand(name="Test", rules=[MaxSlideCount(n=tiny_max)])
    report = brand.validate(deck)
    assert report.ok, "MaxSlideCount should warn, not error"
    assert report.warning_count == 1
    print(f"\n  Triggered MaxSlideCount as warning: {report.violations[0]}")
    deck.close()


def test_forbid_font_families_clean_for_no_forbidden():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    brand = Brand(name="Test",
                  rules=[ForbidFontFamilies(families=["Comic Sans MS", "Papyrus"])])
    report = brand.validate(deck)
    # SVEF is a real production deck — extremely unlikely to use these
    # fonts. If it does, the validator works (and we'd want to know).
    assert report.error_count == 0 or all(
        "Comic Sans MS" in v.message or "Papyrus" in v.message
        for v in report.violations
    )
    print(f"\n  ForbidFontFamilies report: {report.summary()}")
    deck.close()


def test_require_style_name_present_fires_on_missing():
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    brand = Brand(name="Test", rules=[
        RequireStyleNamePresent(
            pbtype="TST.TableStyleArchive",
            name="NoSuchStyle_XYZ123"
        )
    ])
    report = brand.validate(deck)
    assert not report.ok
    assert "NoSuchStyle_XYZ123" in report.violations[0].message
    print(f"\n  Missing-style violation: {report.violations[0]}")
    deck.close()


def test_brand_from_dict_yaml_style_spec():
    """Brand loads from a dict shaped like a YAML rules file."""
    spec = {
        "brand": "Brainworks",
        "version": 1,
        "rules": [
            {"kind": "MinSlideCount", "n": 1},
            {"kind": "ForbidFontFamilies", "families": ["Comic Sans MS"]},
            {"kind": "RequireStyleNamePresent",
             "pbtype": "TST.TableStyleArchive", "name": "Anything"},
        ]
    }
    brand = Brand.from_dict(spec)
    assert brand.name == "Brainworks"
    assert len(brand.rules) == 3
    kinds = [r.kind for r in brand.rules]
    assert kinds == ["MinSlideCount", "ForbidFontFamilies", "RequireStyleNamePresent"]
    print(f"\n  Brand from dict: {brand.name}, rules={kinds}")


def test_brand_from_yaml_file(tmp_path):
    """Brand loads from a real YAML file on disk."""
    yaml_text = """
brand: Brainworks
version: 1
rules:
  - kind: MinSlideCount
    n: 1
  - kind: ForbidFontFamilies
    families: [Comic Sans MS, Papyrus]
"""
    yaml_path = tmp_path / "brand.yaml"
    yaml_path.write_text(yaml_text)
    brand = Brand.from_yaml_file(yaml_path)
    assert brand.name == "Brainworks"
    assert len(brand.rules) == 2
    print(f"\n  Brand from {yaml_path.name}: {len(brand.rules)} rules")


def test_brand_from_dict_rejects_unknown_kind():
    with pytest.raises(ValueError, match="Unknown rule kind"):
        Brand.from_dict({
            "brand": "X", "rules": [{"kind": "BogusRule"}]
        })


def test_available_rules_lists_all_registered():
    rules = available_rules()
    assert "MinSlideCount" in rules
    assert "MaxSlideCount" in rules
    assert "ForbidFontFamilies" in rules
    assert "RequireFontInBodyText" in rules
    assert "RequireStyleNamePresent" in rules
    print(f"\n  Registered rules: {rules}")


def test_full_brand_validation_end_to_end():
    """End-to-end: load a brand spec, validate against SVEF, print
    the report."""
    src = REPO / "recon" / "svef.key"
    if not src.exists():
        pytest.skip("SVEF not available")
    deck = kpa.Deck.from_template(src)
    brand = Brand.from_dict({
        "brand": "Brainworks (smoke test)",
        "version": 1,
        "rules": [
            {"kind": "MinSlideCount", "n": 3},
            {"kind": "ForbidFontFamilies",
             "families": ["Comic Sans MS", "Papyrus", "Wingdings"]},
        ]
    })
    report = brand.validate(deck)
    print(f"\n  === Full validation report ===\n{report}")
    deck.close()
