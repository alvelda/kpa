# KPA — Editable Surface Coverage

**Last updated:** 2026-06-07 17:30 PDT (Step 4c.4 GREEN)

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
| `Shape.fill_color` (solid) | TSWP.ShapeStyleArchive `super.shapeProperties.fill.color` | **round-trip** | test_shape_styling_4c2.py::test_fill_color_round_trip | 4c.2 |
| `Shape.fill` (gradient) | TSWP.ShapeStyleArchive.fill.gradient | `unmapped` | — | 4c.2.2 (gradient/image schema deferred) |
| `Shape.fill` (image) | TSWP.ShapeStyleArchive.fill.image | `unmapped` | — | 4c.2.2 |
| `Shape.stroke_color` | TSWP.ShapeStyleArchive `super.shapeProperties.stroke.color` | **round-trip** | test_shape_styling_4c2.py::test_stroke_color_round_trip | 4c.2 |
| `Shape.stroke_width` | TSWP.ShapeStyleArchive `super.shapeProperties.stroke.width` | **round-trip** | test_shape_styling_4c2.py::test_stroke_width_round_trip | 4c.2 |
| `Shape.stroke_pattern` (none/solid/dashed/dotted) | TSWP.ShapeStyleArchive `super.shapeProperties.stroke.pattern.type` (enum: TSDEmptyPattern/TSDSolidPattern/...) | **round-trip** | test_shape_styling_4c2.py::test_stroke_pattern_round_trip + test_clear_stroke_round_trip | 4c.2 |
| `Shape.shadow` (enabled/color/offset/angle/opacity/radius) | TSWP.ShapeStyleArchive `super.shapeProperties.shadow.*` | **round-trip** | test_shape_styling_4c2.py::test_shadow_round_trip | 4c.2 |
| `Drawable.opacity` | TSWP.ShapeStyleArchive `super.shapeProperties.opacity` | **round-trip** | test_shape_styling_4c2.py::test_opacity_round_trip | 4c.2 |
| `Drawable.reflection` (opacity) | TSWP.ShapeStyleArchive `super.shapeProperties.reflection` | **round-trip** | test_shape_styling_4c2.py::test_reflection_round_trip | 4c.2 |
| `Drawable.angle` (rotation) | geometry.angle | `prototyped` | — | Already in `_Geometry.angle`; needs setter API (4c.2.2) |
| `Drawable.flip_horizontal/vertical` | pathsource.horizontalFlip / verticalFlip | `unmapped` | — | 4c.2.2 |
| `Shape.corner_radius` | pathsource.bezierPathSource | `unmapped` | — | 4c.2.2 |
| `Image.fit_mode` | TSD.ImageArchive.fitType | `unmapped` | — | 4c.2.2 |
| `Image.scale` | TSD.ImageArchive scale | `unmapped` | — | 4c.2.2 |
| `Image.mask` | TSD.MaskArchive | `unmapped` | — | 4c.2.2 |
| `Image.replace(asset_path)` | TSD.ImageArchive + Data/ swap | `unmapped` | — | 4c.2.2 |
| `_ShapeStyleAccessors` mixin (shared) | TSWP.ShapeStyleArchive + Stylesheet | **round-trip** | (implicit — all 4c.2 tests) | 4c.2 |
| `visual_summary()` | resolved shapeProperties | **round-trip** | test_shape_styling_4c2.py::test_read_shape_visuals_from_real_deck | 4c.2 |

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
| `Build.effect` (entrance/exit/action/content) | KN.BuildArchive.attributes.animationAttributes.effect | **round-trip** | test_animations_4c4.py::test_build_effect_round_trip | 4c.4 |
| `Build.animation_type` (In/Out/Action/Content) | KN.BuildArchive.attributes.animationAttributes.animationType | **round-trip** | test_animations_4c4.py::test_build_animation_type_round_trip | 4c.4 |
| `Build.duration` | KN.BuildArchive.attributes.animationAttributes.duration | **round-trip** | test_animations_4c4.py::test_build_duration_delay_round_trip | 4c.4 |
| `Build.delay` | KN.BuildArchive.attributes.animationAttributes.delay | **round-trip** | test_animations_4c4.py::test_build_duration_delay_round_trip | 4c.4 |
| `Build.trigger` (on_click/with_previous/after_previous) | KN.BuildArchive.attributes.eventTrigger | **round-trip** | test_animations_4c4.py::test_build_trigger_round_trip | 4c.4 |
| `Build.text_delivery` (object/paragraph/word/character) | KN.BuildArchive.attributes.customTextDelivery (enum: kTextDeliveryBy*) | **round-trip** (object proven; others best-effort) | test_animations_4c4.py::test_build_text_delivery_round_trip | 4c.4 |
| `Build.delivery_direction` (forward/reverse) | KN.BuildArchive.attributes.customDeliveryOption (enum: kDeliveryOption*) | **round-trip** | test_animations_4c4.py::test_build_text_delivery_round_trip | 4c.4 |
| `Build.target_id` (drawable.identifier) | KN.BuildArchive.drawable.identifier | **round-trip** | (implicit — read test + add_build) | 4c.4 |
| `Slide.builds` | walk slide archives for KN.BuildArchive | **round-trip** | test_animations_4c4.py::test_read_builds_from_real_deck | 4c.4 |
| `Slide.add_build(target, effect=...)` | create new KN.BuildArchive sibling archive | **round-trip** | test_animations_4c4.py::test_add_build_persists | 4c.4 |
| `Slide.remove_build(build)` | delete archive from chunks | **round-trip** | test_animations_4c4.py::test_remove_build_persists | 4c.4 |
| `Slide.find_build(target_id=, effect=)` | linear search helper | `prototyped` | — | 4c.4 |
| `Transition.effect` | KN.SlideArchive.transition.attributes.animationAttributes.effect | **round-trip** | test_animations_4c4.py::test_transition_effect_round_trip | 4c.4 |
| `Transition.duration` | KN.SlideArchive.transition.attributes.animationAttributes.duration | **round-trip** | test_animations_4c4.py::test_transition_duration_delay_round_trip | 4c.4 |
| `Transition.delay` | KN.SlideArchive.transition.attributes.animationAttributes.delay | **round-trip** | test_animations_4c4.py::test_transition_duration_delay_round_trip | 4c.4 |
| `Transition.direction` | KN.SlideArchive.transition.attributes.animationAttributes.direction | **round-trip** | test_animations_4c4.py::test_transition_direction_round_trip | 4c.4 |
| `Transition.is_automatic` | KN.SlideArchive.transition.attributes.animationAttributes.isAutomatic | **round-trip** | test_animations_4c4.py::test_transition_is_automatic_round_trip | 4c.4 |
| Effect alias catalog (`kpa.animations.EFFECTS`) | (internal) — 'fade'/'push'/'fly_in'/'magic_move'/etc. | **round-trip** | (implicit — used in tests) | 4c.4 |
| `Build.build_order` (multi-build sequencing) | KN.BuildArchive chunk position | `unmapped` | — | 4c.4.2 (z-order semantics same as Slide.reorder) |
| `Build.copy_to(other_target)` | clone + re-target helper | `unmapped` | — | 4c.4.2 |

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
| 4c.2 (shape visuals) | 12 | 9 | 3 (rotation, flip, gradient/image fills) |
| 4c.4 (animations + transitions) | 20 | 18 | 2 (build_order, copy_to) |
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
| 2026-06-07 15:15 PDT | 4c.2 GREEN | Shape visual styling: fill_color / stroke (color/width/pattern/clear) / shadow (full param set) / opacity / reflection all round-trip green. 9/9 new tests passing; full suite 24/24 in 9m55s. `_ShapeStyleAccessors` mixin landed on TextBlock + Image. `kpa.styles.resolve_shape_visuals` + `mutate_shape_visual` + `shape_style_id` resolver/writer wired. Engineering finding: visuals live at `super.shapeProperties.{fill,stroke,shadow,opacity,reflection}` of the TSWP.ShapeStyleArchive's TSD base slice; resolver follows the `super` chain leaf-first. Deferred to 4c.2.2: rotation, horizontal/vertical flip (geometry-level, not style-level), gradient/image fills. Visual smoke pending. |
| 2026-06-07 17:30 PDT | 4c.4 GREEN | Animations + transitions: 18 capabilities round-trip green. Build (effect / animation_type / duration / delay / trigger / text_delivery / delivery_direction / target / read+find) + Slide.add_build / remove_build / builds list + Transition (effect / duration / delay / direction / is_automatic) all GREEN. 13/13 new tests; full suite 37/37 in 14m16s. New module `kpa.animations` (Build, Transition, EFFECTS alias catalog with 25 short names mapping to apple:* full strings). Major engineering finding: keynote-parser's binary encoder requires `TSP.ArchiveInfo` header with `messageInfos: [{type: 8, version: [1,0,5]}]` for new KN.BuildArchive sibling archives — plain `{identifier}` headers fail at pack with `messageInfos` error. add_build now emits the correct envelope. Empirical: only `kTextDeliveryByObject` exists in our sample data; paragraph/word/character variants are best-effort writes (may silently drop). Visual smoke pending. |
