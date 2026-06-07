# Slide-Kind Inventory — SVEF + NCI

**Generated:** by `scripts/slide_kind_inventory.py`
**Step:** 4a (Captain Q3 — slide-kind taxonomy seeded from reference decks)

## Combined kind counts

| Kind | Slides across both decks |
|---|---|
| `text_image` | 104 |
| `bullet_list` | 40 |

## SVEF (59 slides)

### Slides by kind

| Kind | Count |
|---|---|
| `text_image` | 59 |

### Top template-slide (master) references

| Template ID | # slides using it |
|---|---|
| `652` | 58 |
| `821` | 1 |

### Placeholder kinds observed

| Placeholder kind enum | Count |
|---|---|
| `kKindSlideNumberPlaceholder` | 59 |
| `kKindTitlePlaceholder` | 59 |
| `kKindBodyPlaceholder` | 59 |

## NCI (85 slides)

### Slides by kind

| Kind | Count |
|---|---|
| `text_image` | 45 |
| `bullet_list` | 40 |

### Top template-slide (master) references

| Template ID | # slides using it |
|---|---|
| `495` | 73 |
| `36054` | 6 |
| `36055` | 4 |
| `115866` | 1 |
| `36062` | 1 |

### Placeholder kinds observed

| Placeholder kind enum | Count |
|---|---|
| `kKindTitlePlaceholder` | 85 |
| `kKindBodyPlaceholder` | 85 |
| `kKindSlideNumberPlaceholder` | 85 |

## Interpretation

The kind labels above are heuristic, derived from structural fingerprints (counts of text/image/chart/table/shape archives + title/body/byline placeholder hints). The final `kpa.slide_kinds` library will use these as seeds and add semantic role tags (`title`, `text_image`, `bullet_list`, `quote`, `closing`, `section_divider`, `chart`, `table`, `image_only`, `text_only`) during Step 4b/4c as we author against them.

Master-slide references show which template slides each deck reuses most heavily — those are the high-value cloning targets for the template-anchored authoring flow in Step 4b.
