# KPA — Editable Surface Coverage

**Last updated:** 2026-06-07 11:00 PDT (Step 4c.1 GREEN)

Per Captain 2026-06-07 08:28 PDT, KPA must address every editable
element in the `.key` file structure. This is the live coverage tracker
for the F2d success criterion.

## Status legend

| Status | Meaning |
|---|---|
| `unmapped` | Not yet implemented; no test, no API |
| `prototyped` | Reads work, writes work in isolation; no round-trip test yet |
| `round-trip` | Round-trip test green: load → mutate → save → reopen confirms persistence |
| `visual-verified` | Plus: opened in Keynote 14.5, rendered correctly |
| `production` | Plus: documented, has examples, brand-validator-aware |

## Coverage matrix

### 4c.1 — Text styling

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `TextBlock.text` get/set | TSWP.StorageArchive.text | **round-trip** | test_edits.py::test_text_edit_and_move_round_trip | Step 4b |
| `TextBlock.position`, `.size` | shape geometry | **round-trip** | test_edits.py | Step 4b |
| `TextBlock.move(dx, dy)` | shape geometry | **round-trip** | test_edits.py | Step 4b |
| `TextBlock.font_name` | TSWP.CharacterStyleArchive.fontName | **round-trip** | test_styling_4c1.py::test_font_name_round_trip | 4c.1 |
| `TextBlock.font_size` | TSWP.CharacterStyleArchive.fontSize | **round-trip** | test_styling_4c1.py::test_font_size_round_trip | 4c.1 |
| `TextBlock.bold` (font_weight) | TSWP.CharacterStyleArchive.bold | **round-trip** | test_styling_4c1.py::test_bold_italic_underline_round_trip | 4c.1 |
| `TextBlock.italic` | TSWP.CharacterStyleArchive.italic | **round-trip** | test_styling_4c1.py::test_bold_italic_underline_round_trip | 4c.1 |
| `TextBlock.underline` (+ `.underline_style`) | TSWP.CharacterStyleArchive.underline (enum: kNo/kSingle/kDouble/kDotted/kDashed/kWavy) | **round-trip** | test_styling_4c1.py::test_bold_italic_underline_round_trip | 4c.1 |
| `TextBlock.color` (Color value type) | TSWP.CharacterStyleArchive.fontColor + tsdFill.color (RGBA) | **round-trip** | test_styling_4c1.py::test_color_round_trip | 4c.1 |
| `TextBlock.alignment` (+ `.alignment_name`) | TSWP.ParagraphStyleArchive.alignment (enum: TATvalue0..4) | **round-trip** | test_styling_4c1.py::test_alignment_round_trip | 4c.1 |
| `TextBlock.line_spacing` | TSWP.ParagraphStyleArchive.lineSpacing (dict: amount+mode) | **round-trip** | test_styling_4c1.py::test_line_spacing_round_trip | 4c.1 |
| `TextBlock.first_line_indent` | TSWP.ParagraphStyleArchive.firstLineIndent | `prototyped` | — | 4c.1 (no test yet, API live) |
| `TextBlock.space_before` | TSWP.ParagraphStyleArchive.spaceBefore | **round-trip** | test_styling_4c1.py::test_paragraph_spacing_round_trip | 4c.1 |
| `TextBlock.space_after` | TSWP.ParagraphStyleArchive.spaceAfter | **round-trip** | test_styling_4c1.py::test_paragraph_spacing_round_trip | 4c.1 |
| `TextBlock.style_summary()` (resolves chain) | TSS.StylesheetArchive walker via `kpa.styles.resolve_props` | **round-trip** | test_styling_4c1.py::test_read_styles_from_real_deck | 4c.1 |
| `TextBlock.bullet_style` | TSWP.ListStyleArchive | `unmapped` | — | 4c.1 (deferred to 4c.1.2) |
| `TextBlock.list_level` | TSWP.ListStyleArchive | `unmapped` | — | 4c.1 (deferred to 4c.1.2) |
| `TextBlock.runs` (per-character) | TSWP.StorageArchive.tableParaStyle + tableCharStyle | `unmapped` | — | 4c.1 (deferred to 4c.1.2) |
| DropCap support | TSWP.DropCapStyleArchive | `unmapped` | — | 4c.1 (deferred to 4c.1.2) |
| **Color value type** (`kpa.Color`) | RGBA dict serializer | **round-trip** | test_styling_4c1.py::test_color_value_type_smoke | 4c.1 |
| **Stylesheet resolver** (`kpa.styles.Stylesheet`) | DocumentStylesheet.iwa.yaml + parent-chain walk | **round-trip** | (implicit in all 4c.1 tests) | 4c.1 |

### 4c.2 — Shape styling + visual effects

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Shape.fill` (color) | TSWP.ShapeStyleArchive.fill | `unmapped` | — | 4c.2 |
| `Shape.fill` (gradient) | TSWP.ShapeStyleArchive.fill.gradient | `unmapped` | — | 4c.2 |
| `Shape.fill` (image) | TSWP.ShapeStyleArchive.fill.image | `unmapped` | — | 4c.2 |
| `Shape.stroke` (color, width, dash) | TSWP.ShapeStyleArchive.stroke | `unmapped` | — | 4c.2 |
| `Shape.shadow` | TSWP.ShapeStyleArchive.shadow | `unmapped` | — | 4c.2 |
| `Drawable.opacity` | drawable.opacity | `unmapped` | — | 4c.2 |
| `Shape.corner_radius` | pathsource.bezierPathSource | `unmapped` | — | 4c.2 |
| `Drawable.angle` | geometry.angle | `prototyped` | — | Already in geometry dict; needs API |
| `.flip_horizontal()`, `.flip_vertical()` | pathsource.horizontalFlip / verticalFlip | `unmapped` | — | 4c.2 |
| `Image.fit_mode` | TSD.ImageArchive.fitType | `unmapped` | — | 4c.2 |
| `Image.scale` | TSD.ImageArchive scale | `unmapped` | — | 4c.2 |
| `Image.mask` | TSD.MaskArchive | `unmapped` | — | 4c.2 |
| `Image.replace(asset_path)` | TSD.ImageArchive + Data/ swap | `unmapped` | — | 4c.2 |

### 4c.3 — Layout + structure

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Slide.bring_to_front(elem)` | KN.SlideArchive.drawablesZOrder | `unmapped` | — | 4c.3 |
| `Slide.send_to_back(elem)` | KN.SlideArchive.drawablesZOrder | `unmapped` | — | 4c.3 |
| `Slide.reorder([...])` | KN.SlideArchive.drawablesZOrder | `unmapped` | — | 4c.3 |
| `Slide.group([a, b, c])` | TSD.GroupArchive | `unmapped` | — | 4c.3 |
| `Group.ungroup()` | TSD.GroupArchive | `unmapped` | — | 4c.3 |
| `Slide.guides` (add/remove/list) | TSD.GuideStorageArchive | `unmapped` | — | 4c.3 |
| `Slide.notes` get/set | KN.NoteArchive | `unmapped` | — | 4c.3 |

### 4c.4 — Animations + transitions

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Element.entrance(effect, duration, delay)` | KN.BuildArchive | `unmapped` | — | 4c.4 |
| `Element.exit(...)` | KN.BuildArchive | `unmapped` | — | 4c.4 |
| `Element.emphasis(...)` | KN.BuildArchive | `unmapped` | — | 4c.4 |
| `Element.build_order` | KN.BuildArchive ordering | `unmapped` | — | 4c.4 |
| `Slide.transition` | transition dict on KN.SlideArchive | `unmapped` | — | 4c.4 |
| Effect-id catalog | (internal mapping) | `unmapped` | — | 4c.4 |

### 4c.5 — Media (video + audio)

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Video.loop` | TSD.MovieArchive | `unmapped` | — | 4c.5 |
| `Video.autoplay` | TSD.MovieArchive | `unmapped` | — | 4c.5 |
| `Video.start_time`, `.end_time` (trim) | TSD.MovieArchive | `unmapped` | — | 4c.5 |
| `Video.audio_level` | TSD.MediaStyleArchive | `unmapped` | — | 4c.5 |
| `Video.poster_frame_time` | TSD.MovieArchive | `unmapped` | — | 4c.5 |
| `Video.show_controls` | TSD.MovieArchive | `unmapped` | — | 4c.5 |
| `Video.replace(asset_path)` | TSD.MovieArchive + Data/ swap | `unmapped` | — | 4c.5 |
| `Deck.soundtrack` | KN.Soundtrack | `unmapped` | — | 4c.5 |
| `Slide.motion_background` | KN.MotionBackgroundStyleArchive | `unmapped` | — | 4c.5 |
| `LiveVideo` proxy (read) | KN.LiveVideoSource | `unmapped` | — | 4c.5 |

### 4c.6 — Charts + tables (pass-through styling)

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Chart.style` | TSCH.ChartStyleArchive | `unmapped` | — | 4c.6 |
| `Chart.series[i].color` | TSCH.ChartSeriesStyleArchive | `unmapped` | — | 4c.6 |
| `Chart.axis.title`, `.labels` | TSCH.ChartAxisStyleArchive | `unmapped` | — | 4c.6 |
| `Chart.legend.visible`, `.position` | TSCH.LegendStyleArchive | `unmapped` | — | 4c.6 |
| `Table.cell(r,c).value` get/set | TST.* | `unmapped` | — | 4c.6 |
| `Table.cell(r,c).set_style(...)` | TST.CellStyleArchive | `unmapped` | — | 4c.6 |
| Full chart object model | TSCH.* | `unmapped` | — | **Step 5** |
| Full table object model | TST.* | `unmapped` | — | **Step 5** |

### 4c.7 — Universal escape hatch

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Slide.raw_archive(id_or_pbtype)` | any | `unmapped` | — | 4c.7 |
| `Deck.raw_archive(path)` | document-level | `unmapped` | — | 4c.7 |

### 4c.8 — Slide-kind library + brand validator + asset grovel

| Capability | Status | Notes |
|---|---|---|
| `section_divider` slide kind | `unmapped` | 4c.8 |
| `quote` slide kind | `unmapped` | 4c.8 |
| `closing` slide kind | `unmapped` | 4c.8 |
| `kpa.Theme` (partial) | `unmapped` | 4c.8 |
| `kpa.BrandComplianceValidator` | `unmapped` | 4c.8 |
| `kpa harvest` CLI | `unmapped` | 4c.8 |
| `kpa.BrandAssetLibrary` | `unmapped` | 4c.8 |

## Coverage summary

| Sub-step | Capabilities | round-trip ✅ | unmapped |
|---|---|---|---|
| 4a/4b (done) | 6 | 6 | 0 |
| 4c.1 (text styling) | 20 | 13 | 7 (bullets, list_level, runs, dropcap, first_line_indent test) |
| 4c.2 (shape + effects) | 13 | 0 | 13 |
| 4c.3 (layout) | 7 | 0 | 7 |
| 4c.4 (animations) | 6 | 0 | 6 |
| 4c.5 (media) | 10 | 0 | 10 |
| 4c.6 (charts/tables pass-through) | 6 | 0 | 6 |
| 4c.7 (escape hatch) | 2 | 0 | 2 |
| 4c.8 (kinds + validator + grovel) | 7 | 0 | 7 |
| **TOTAL Step 4c target** | **69** | 0 | 69 |

## Progress log

| Date | Sub-step | Note |
|---|---|---|
| 2026-06-07 08:35 PDT | 4c kickoff | Coverage matrix initialized; Step 4c plan committed (PRD v1.3, DEV_PLAN updated). |
| 2026-06-07 11:00 PDT | 4c.1 GREEN | Text styling: font/size/bold/italic/underline/color/alignment/line-spacing/space-before/space-after all round-trip green. 9/9 new tests passing; full suite 15/15 in 5m41s. `kpa.color.Color` value type + `kpa.styles.Stylesheet` resolver + `mutate_char_prop`/`mutate_para_prop` write path landed. Deferred to 4c.1.2: bullet/list_level/runs/dropcap (need more design for ListStyleArchive + per-run write semantics). Visual smoke pending. |
