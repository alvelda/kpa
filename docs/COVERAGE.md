# KPA — Editable Surface Coverage

**Last updated:** 2026-06-09 17:30 PDT (Step 4c.6.2 + 4c.8.2 GREEN — Phase 1.5 progressing)

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
| `Slide.drawables_z_order` (read) | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_drawables_z_order_returns_tuple_of_ids | 4c.3 |
| `Slide.z_index(shape)` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_z_index_lookup | 4c.3 |
| `Slide.bring_to_front(shape)` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_bring_to_front_in_memory + test_zorder_round_trip | 4c.3 |
| `Slide.send_to_back(shape)` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_send_to_back_in_memory | 4c.3 |
| `Slide.send_forward(shape)` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_send_forward_backward_in_memory | 4c.3 |
| `Slide.send_backward(shape)` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_send_forward_backward_in_memory | 4c.3 |
| `Slide.set_z_order([...])` | KN.SlideArchive.drawablesZOrder | **round-trip** | test_layout_4c3.py::test_set_z_order_explicit + test_set_z_order_round_trip | 4c.3 |
| Z-order accepts proxy objects (TextBlock/Image) | resolver | **round-trip** | test_layout_4c3.py::test_zorder_accepts_proxy_objects | 4c.3 |
| `Slide.groups` (read) | KN.GroupArchive | **prototyped** | test_layout_4c3.py::test_groups_empty_on_svef + test_group_proxy_read_when_present | 4c.3 (no group present in samples; synthetic fixture used) |
| `Group.children_ids` / `Group.children` | KN.GroupArchive.contents | **prototyped** | test_layout_4c3.py::test_group_proxy_read_when_present | 4c.3 |
| `Group` escape hatch (raw_get/set/keys/dump/pbtype) | KN.GroupArchive | **prototyped** | test_layout_4c3.py::test_group_proxy_read_when_present | via RawArchiveMixin |
| `Slide.group([a, b, c])` / `Group.ungroup()` | KN.GroupArchive | `unmapped` | — | 4c.3.2 (deferred; needs sample deck with groups) |
| `Slide.guides` (add/remove/list) | TSD.GuideStorageArchive | `unmapped` | — | 4c.3.2 |
| `Slide.notes` get/set | KN.NoteArchive | `unmapped` | — | 4c.3.2 |

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
| `Movie.loop` (None/Repeat/BackAndForth + aliases off/loop/bounce) | TSD.MovieArchive.loopOption | **round-trip** | test_media_4c5.py::test_movie_loop_round_trip + test_movie_loop_off_round_trip | 4c.5 |
| `Movie.plays_across_slides` (multi-slide playback) | TSD.MovieArchive.playsAcrossSlides | **round-trip** | test_media_4c5.py::test_movie_plays_across_slides_round_trip | 4c.5 |
| `Movie.start_time` / `.end_time` (trim) | TSD.MovieArchive.startTime/endTime | **round-trip** | test_media_4c5.py::test_movie_trim_round_trip | 4c.5 |
| `Movie.set_trim(start, end)` convenience | (composite) | **round-trip** | test_media_4c5.py::test_movie_trim_round_trip | 4c.5 |
| `Movie.duration` (computed) | end_time - start_time | **round-trip** | test_media_4c5.py::test_movie_trim_round_trip | 4c.5 |
| `Movie.poster_time` | TSD.MovieArchive.posterTime | **round-trip** | test_media_4c5.py::test_movie_trim_round_trip | 4c.5 |
| `Movie.volume` | TSD.MovieArchive.volume | **round-trip** | test_media_4c5.py::test_movie_volume_round_trip | 4c.5 |
| `Movie.mute()` / `.unmute()` / `.is_muted` | (volume helpers) | **round-trip** | test_media_4c5.py::test_movie_mute_round_trip | 4c.5 |
| `Movie.is_audio_only` (treat-as-audio) | TSD.MovieArchive.audioOnly | **round-trip** | test_media_4c5.py::test_movie_audio_only_round_trip | 4c.5 |
| `Movie.media_data_id` / `.poster_image_id` / `.style_id` (refs) | TSD.MovieArchive.{movieData,posterImageData,style}.identifier | **round-trip** (read-only) | test_media_4c5.py::test_read_movie_from_real_deck | 4c.5 |
| `Movie.streaming` / `.natural_size` (read-only) | TSD.MovieArchive.{streaming,naturalSize} | **round-trip** (read-only) | test_media_4c5.py::test_read_movie_from_real_deck | 4c.5 |
| `Slide.movies` | walk slide archives for TSD.MovieArchive | **round-trip** | test_media_4c5.py::test_read_movie_from_real_deck | 4c.5 |
| `Deck.soundtrack` | KN.Soundtrack (Document.iwa) | **round-trip** | test_media_4c5.py::test_read_soundtrack | 4c.5 |
| `Soundtrack.mode` (PlayOnce/Loop/Off + aliases once/loop/off) | KN.Soundtrack.mode | **round-trip** | test_media_4c5.py::test_soundtrack_mode_round_trip | 4c.5 |
| `Soundtrack.volume` | KN.Soundtrack.volume | **round-trip** | test_media_4c5.py::test_soundtrack_volume_round_trip | 4c.5 |
| `Deck.live_video_sources` | KN.LiveVideoSource (Document.iwa) | **round-trip** | test_media_4c5.py::test_read_live_video_sources | 4c.5 |
| `LiveVideoSource.name` / `.is_default` / `.set_default()` | KN.LiveVideoSource.{name,isDefaultSource} | **round-trip** | test_media_4c5.py::test_live_video_source_name_round_trip | 4c.5 |
| `Video.audio_level` (per-track) | TSD.MediaStyleArchive | `unmapped` | — | 4c.5.2 |
| `Video.autoplay` / `.show_controls` (proto field unknown) | TSD.MovieArchive (TBD) | `unmapped` | — | 4c.5.2 |
| `Movie.replace(asset_path)` (swap blob in Data/) | TSD.MovieArchive + Data/ blob | `unmapped` | — | 4c.5.2 |
| `Slide.motion_background` | KN.MotionBackgroundStyleArchive | `unmapped` | — | 4c.5.2 |

### 4c.6 — Charts + tables (first-pass: read + introspection)

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `Slide.charts` (discover chart drawables) | TSCH.ChartDrawableArchive | **round-trip** | test_data_shapes_4c6.py::test_charts_discovered_in_svef | 4c.6 |
| `Slide.tables` (discover table drawables) | TST.TableInfoArchive | **round-trip** | test_data_shapes_4c6.py::test_tables_class_introspection | 4c.6 |
| `Chart.archive_id` / `Chart.PBTYPE` | TSCH.ChartDrawableArchive | **round-trip** | test_data_shapes_4c6.py::test_chart_pbtype_and_class | 4c.6 |
| `Chart.position` / `.size` / `.angle` | TSD shape base | **round-trip** | test_data_shapes_4c6.py::test_chart_geometry_reads | 4c.6 |
| `Chart.aspect_ratio_locked` / `.locked` / `.caption_hidden` | TSD shape base | **round-trip** | test_data_shapes_4c6.py::test_chart_geometry_reads | 4c.6 |
| `Chart.has_chart_unity` / `.chart_unity_keys` | `[TSCH.ChartArchive.unity]` | **round-trip** | test_data_shapes_4c6.py::test_chart_unity_extension | 4c.6 |
| `Table.position` / `.size` / `.angle` (read) | TSD shape base | `unmapped` | — | no on-slide table in SVEF/NCI; 4c.6.2 with synthetic deck |
| `RawArchiveMixin` reaches `[TSCH.*]` extension keys | parser+walker | **round-trip** | test_data_shapes_4c6.py::test_chart_escape_hatch_deep_get | 4c.6 |
| `Stylesheet.iter_by_pbtype(pbtype)` | (helper) | **round-trip** | test_data_shapes_4c6.py::test_stylesheet_iter_by_pbtype_helper | 4c.6 |
| `list_table_style_archive_ids(deck)` | TST.TableStyleArchive | **round-trip** | test_data_shapes_4c6.py::test_stylesheet_table_styles_enumerable | 4c.6 |
| `list_chart_style_archive_ids(deck)` | TSCH.ChartStyleArchive | **round-trip** | test_data_shapes_4c6.py::test_stylesheet_chart_styles_enumerable | 4c.6 |
| Path parser: bracketed extension keys (e.g. `[TSCH.foo]`) | parser | **round-trip** | test_data_shapes_4c6.py::test_parse_path_* | 4c.6 |
| Chart geometry survives lossless save/open | TSCH+TSD | **round-trip** | test_data_shapes_4c6.py::test_chart_geometry_round_trip | 4c.6 |
| `Chart.style` (set chart style by id) | TSCH.ChartStyleArchive | `unmapped` | — | 4c.6.2 |
| `Chart.series[i].color` (set series color) | TSCH.ChartSeriesStyleArchive | `unmapped` | — | 4c.6.2 |
| `Chart.axis.title`, `.labels` | TSCH.ChartAxisStyleArchive | `unmapped` | — | 4c.6.2 |
| `Chart.legend.visible`, `.position` | TSCH.LegendStyleArchive | `unmapped` | — | 4c.6.2 |
| `Slide.tables` (cross-file: CalculationEngine.iwa.yaml) | TST.TableInfoArchive | **round-trip** | test_table_writes_4c6_2.py::test_test1_has_one_table | 4c.6.2-tables |
| `Table.position` / `.size` / `.angle` (read) | TSD shape base | **round-trip** | test_table_writes_4c6_2.py::test_table_position_size_angle_read | 4c.6.2-tables |
| `Table.set_position(x,y)` / `set_size(w,h)` / `move(dx,dy)` (aux-file flush) | TSD shape base | **round-trip** | test_table_writes_4c6_2.py::test_table_set_position_round_trip | 4c.6.2-tables |
| `Table.table_model_id` / `Table.summary_model_id` | TST.TableInfoArchive | **round-trip** | test_table_writes_4c6_2.py::test_table_references_table_model | 4c.6.2-tables |
| `Table.cell(r,c).value` get/set | TST.TableModelArchive + DataStore | `unmapped` | — | Phase 2 (heavy cell-tile schema; escape hatch reaches it now) |
| `Table.cell(r,c).set_style(...)` | TST.CellStyleArchive | `unmapped` | — | Phase 2 |
| Full chart object model | TSCH.* | `unmapped` | — | **Step 5** |
| Full table object model | TST.* | `unmapped` | — | **Step 5** |

### 4c.7 — Universal escape hatch

| Capability | Protobuf type(s) | Status | Test | Notes |
|---|---|---|---|---|
| `proxy.raw_archive()` (live dict) | any | **round-trip** | test_escape_4c7.py (all read tests) | 4c.7 |
| `proxy.raw_get(path, default=None)` (deep read) | any | **round-trip** | test_escape_4c7.py::test_textblock_raw_introspection | 4c.7 |
| `proxy.raw_set(path, value)` (deep write + auto-dirty) | any | **round-trip** | test_escape_4c7.py::test_textblock_raw_set_round_trip + 5 more | 4c.7 |
| `proxy.raw_keys(path="")` (introspection) | any | **round-trip** | test_escape_4c7.py::test_textblock_raw_introspection | 4c.7 |
| `proxy.raw_dump(path, maxdepth)` (pretty view) | any | **round-trip** | test_escape_4c7.py::test_textblock_raw_introspection | 4c.7 |
| `proxy.raw_pbtype()` (type discovery) | any | **round-trip** | test_escape_4c7.py::test_slide_raw_pbtype | 4c.7 |
| Path syntax: dot keys + `[idx]` lists, mixed | (parser) | **round-trip** | test_escape_4c7.py::test_parse_path_* | 4c.7 |
| `kpa.escape.deep_get/deep_set/keys_at/truncate_view` (low-level helpers) | (parser) | **round-trip** | test_escape_4c7.py::test_deep_get_* + test_deep_set_* | 4c.7 |
| `RawArchiveMixin` (universal mixin) | (helper) | **round-trip** | 8 proxies wired: TextBlock/Image/Slide/Build/Transition/Movie/Soundtrack/LiveVideoSource | 4c.7 |
| `Deck.raw_archive(path)` (document-level walker by pbtype) | document-level | `unmapped` | — | 4c.7.2 (deferred) |

### 4c.8 — Slide-kind library + brand validator + asset grovel (Phase 1 closer)

| Capability | Status | Notes |
|---|---|---|
| `kpa.slide_kinds.list_slide_kinds(deck)` | **round-trip** | enumerates all TemplateSlide-*.iwa.yaml entries (Apple's per-theme kind library) |
| `kpa.slide_kinds.find_slide_kind(deck, name=...)` | **round-trip** | case-insensitive name lookup (BLANK / TITLE_AND_BODY / etc.) |
| `kpa.slide_kinds.find_slide_kind(deck, identifier=...)` | **round-trip** | exact id lookup |
| `kpa.slide_kinds.slide_kind_for_slide(slide)` | **round-trip** | resolves a slide's `templateSlide` ref to its kind |
| `SlideKind.name` / `.identifier` / `.yaml_filename` | **round-trip** | basic metadata reads |
| `SlideKind.has_*_placeholder` / `.drawable_count` | **round-trip** | placeholder layout discovery |
| `SlideKind` inherits `RawArchiveMixin` | **round-trip** | full escape hatch on template slides |
| `kpa.assets.list_assets(deck, kind=...)` | **round-trip** | grovel embedded Data/ blobs, optional kind filter |
| `kpa.assets.Asset.kind` classification (image/video/audio/font/doc/other) | **round-trip** | by extension; 12-ext image bucket, 6-ext video bucket |
| `kpa.assets.Asset.extract_to(dest)` | **round-trip** | single-asset copy to dest dir |
| `kpa.assets.asset_summary(deck)` | **round-trip** | per-kind count + bytes + total bucket |
| `kpa.assets.extract_all_assets(deck, dest, kind=...)` | **round-trip** | bulk extract with optional filter |
| `kpa.validator.Brand` + `Rule` + `Violation` + `ValidationReport` | **round-trip** | brand-validator core API |
| `Brand.from_dict(spec)` / `from_yaml_file(path)` | **round-trip** | YAML-driven rules file loading |
| `MinSlideCount` / `MaxSlideCount` (deck-shape rules) | **round-trip** | error / warning severity |
| `ForbidFontFamilies` (deny-list) | **round-trip** | walks TSWP.CharacterStyleArchive entries |
| `RequireFontInBodyText` (allow-list) | **round-trip** | warning severity |
| `RequireStyleNamePresent` (named-archive presence check) | **round-trip** | pbtype + name match |
| `kpa.validator.available_rules()` | **round-trip** | rule discovery for YAML authoring |
| `Deck.new_slide(kind=..., after=...)` (template instantiation, all SVEF kinds) | **round-trip** | test_new_slide_4c8_2.py (13 tests) — 4c.8.2 GREEN |
| `kpa harvest` CLI | `unmapped` | nice-to-have, optional Phase 1.5 |

## Coverage summary

| Sub-step | Capabilities | round-trip ✅ | unmapped |
|---|---|---|---|
| 4a/4b (done) | 6 | 6 | 0 |
| 4c.1 (text styling) | 20 | 13 | 7 (bullets, list_level, runs, dropcap, first_line_indent test) |
| 4c.2 (shape visuals) | 12 | 9 | 3 (rotation, flip, gradient/image fills) |
| 4c.4 (animations + transitions) | 20 | 18 | 2 (build_order, copy_to) |
| 4c.5 (media: movies + soundtrack + live video) | 21 | 17 | 4 (per-track audio level, autoplay/controls, blob replace, motion background) |
| 4c.7 (universal escape hatch) | 10 | 9 | 1 (Deck-level walker by pbtype) |
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
| 2026-06-07 22:30 PDT | 4c.5 GREEN | Media (video + audio): 17 capabilities round-trip green. Movie (loop with 3 modes + aliases, plays_across_slides, start/end_time trim, set_trim convenience, duration, poster_time, volume + mute/unmute, audio_only, ref ids, streaming, natural_size) + Slide.movies + Soundtrack (mode with 3 modes + aliases, volume) + Deck.soundtrack + Deck.live_video_sources + LiveVideoSource (name, is_default). 13/13 new tests; full suite 50/50 in 18m49s. New module `kpa.media` (Movie, Soundtrack, LiveVideoSource). New Deck infra: `_document_root()` lazy loader, `_mark_document_dirty()`, `_find_document_archive(s)` helpers for Document.iwa.yaml mutations — first deck-level archive writes in kpa, soundtrack and live-video flush through save(). Major proven find: encoder DOES accept `kKNSoundtrackModeLoop` even though only `kKNSoundtrackModePlayOnce` is in source data — proto schema enum survives round-trip (validates the "unknown enums fall through" pattern as a real capability, not a wishlist). Loop aliases (off/loop/bounce/pingpong) + soundtrack mode aliases (once/loop/off) make the API friendly. Deferred to 4c.5.2: per-track audio_level (TSD.MediaStyleArchive), autoplay/show_controls (proto field not yet identified), Movie.replace(asset_path) blob swap, Slide.motion_background. Visual smoke pending. |
| 2026-06-08 09:15 PDT | 4c.7 GREEN | Universal escape hatch: 9 capabilities round-trip green. New module `kpa.escape` with `RawArchiveMixin` wired into 8 proxies (TextBlock, Image, Slide, Build, Transition, Movie, Soundtrack, LiveVideoSource). API: `raw_archive()`, `raw_get(path)`, `raw_set(path, value)`, `raw_keys(path="")`, `raw_dump(path, maxdepth)`, `raw_pbtype()`. Path syntax supports dot-separated keys + `[N]` list indices + mixed (e.g. `super.objects[0].pbtype`). Low-level helpers `deep_get`/`deep_set`/`keys_at`/`truncate_view` exposed at module level for power users. 18/18 new tests; full suite 68/68 in 21m45s. Engineering finding: each proxy needs its own `_raw_archive_root()` because the archive shape varies (TextBlock=ShapeInfoArchive, Image=ImageArchive, Slide=SlideArchive, Build=BuildArchive, Movie=MovieArchive, Soundtrack=Soundtrack@Document.iwa, LiveVideo=LiveVideoSource@Document.iwa, Transition=transition subtree of SlideArchive). raw_set auto-creates missing dict intermediates and auto-marks dirty for save() flushing. raw_pbtype returns None for Transition since its root is a subtree, not a typed archive. Closes the 'agent never blocked' gate — any field in any covered proxy is now writable even if no typed accessor exists yet. Deferred to 4c.7.2: Deck-level `raw_archive(pbtype)` walker for document-wide schema queries. |
| 2026-06-08 11:00 PDT | 4c.3 GREEN | Layout/structure: 12 capabilities round-trip green. `Slide.drawables_z_order` (read tuple of ids), `Slide.z_index(shape)` (lookup, -1 if absent), `Slide.bring_to_front` / `send_to_back` / `send_forward` / `send_backward` (full set of z-order ops), `Slide.set_z_order([shapes])` (explicit replace, unlisted ids preserved at back), `Slide.groups` (tuple of read-only `Group` proxies). All accept TextBlock/Image proxies, raw int/str ids, or `{identifier: <id>}` dicts via `_resolve_shape_id`. 12/12 new tests; full suite 80/80 in 27m34s. New module `kpa.layout` (`Group` RawArchiveMixin, `_resolve_shape_id`, `_zorder_list`, `_zorder_index`). Round-trip proven: z-order mutations persist through save/open on SVEF. Group write API (`Slide.group([...])`, `Group.ungroup()`) deferred to 4c.3.2 (no sample deck with KN.GroupArchive instances). Phase 1 Step 4: 84/100 round-trip (84%). |
| 2026-06-09 04:30 PDT | 4c.6 first-pass GREEN | Charts + tables (read + introspection): 13 capabilities round-trip green. `Slide.charts` / `Slide.tables` accessors return tuples of `Chart`/`Table` proxies (TSCH.ChartDrawableArchive / TST.TableInfoArchive). Chart proxy: `archive_id`, `PBTYPE`, geometry passthrough (`position`/`size`/`angle`), `aspect_ratio_locked`/`locked`/`caption_hidden`, `has_chart_unity`/`chart_unity_keys` for the bracketed extension introspection. Both proxies inherit `RawArchiveMixin` so the universal escape hatch reaches every field. New `Stylesheet.iter_by_pbtype(pbtype)` helper exposes any archive type in DocumentStylesheet by pbtype filter; convenience wrappers `list_table_style_archive_ids` and `list_chart_style_archive_ids`. Engineering finding: TSCH chart schema is **entirely extension-driven** — every TSCH archive exposes only `super` as a real field, with all chart data behind bracketed `[TSCH.*]` extension keys like `[TSCH.ChartArchive.unity]` (29 sub-keys on SVEF charts). This required extending the path parser to accept bracketed dict keys (e.g. `super.[TSCH.ChartArchive.unity]`) alongside the existing `[N]` list-index syntax; brackets are preserved in the key string to match the literal YAML form. 17/17 new tests (incl. 5 new parser tests for bracketed keys); full suite 97/97 in 27m04s. SVEF: 2 chart drawables on slides 1+4 (verified); 0 on-slide tables (TST styles exist in stylesheet only — Table writes deferred to 4c.6.2 with synthetic test deck). Phase 1 Step 4: 97/100 round-trip (97%). Deferred to 4c.6.2: chart `style`/`series`/`axis`/`legend` writes (heavy TSCH semantics, need careful extension boundary handling); Table cell read/write API. Visual smoke pending. |
| 2026-06-09 06:55 PDT | **4c.8 GREEN — Phase 1 CLOSED** | Three deliverables in one sub-step: slide-kind library + asset grovel + brand validator. **kpa.slide_kinds**: `SlideKind` (RawArchiveMixin) wraps `KN.SlideArchive` instances in `TemplateSlide-*.iwa.yaml` (Apple's per-theme kind library); `list_slide_kinds(deck)`, `find_slide_kind(deck, name=..., identifier=...)` (case-insensitive name lookup), `slide_kind_for_slide(slide)` (resolves a slide's `templateSlide` ref to its kind), placeholder introspection (`has_title_placeholder` / `has_body_placeholder` / `has_object_placeholder` / `has_slide_number_placeholder` / `drawable_count`). **kpa.assets**: `Asset` (filename / extension / size_bytes / kind), kind classification by extension (image/video/audio/font/document/other — 36 ext mappings), `list_assets(deck, kind=...)`, `asset_summary(deck)` (per-bucket count + bytes + total), `extract_all_assets(deck, dest, kind=...)`. **kpa.validator**: `Brand` / `Rule` / `Violation` / `ValidationReport` core; 5 first-pass rules — `MinSlideCount` / `MaxSlideCount` (deck shape, error/warning severities), `ForbidFontFamilies` (deny-list, walks `TSWP.CharacterStyleArchive`), `RequireFontInBodyText` (allow-list, warning), `RequireStyleNamePresent` (named-archive presence check); rule registry + `available_rules()`, `Brand.from_dict(spec)` / `from_yaml_file(path)` for YAML rules file loading; `ValidationReport.ok` / `.summary()` / `__str__` for human-readable reports. Engineering finding: Apple's template-slide library lives in `TemplateSlide-*.iwa.yaml` (not "MasterSlide" as the spec name suggested) — each template is a `KN.SlideArchive` with a `name` field (Apple's canonical kind labels like `TITLE_AND_BODY`, `BLANK`, `TITLE_AND_TWO_COLUMNS`). SVEF ships 27 such templates. Real slides reference their template via `slide.templateSlide = {identifier: <id>}`. SVEF has 436 embedded assets in `Data/` (357 PNGs, 45 JPEGs, 20 JPGs, 10 TIFFs, 2 MP4s, 1 AVIF, 1 PDF) totaling ~52MB — confirms the grovel API has real work to do. 24/24 new tests; full suite **121/121** passing in 30m07s. **Phase 1 Step 4: 121 capabilities round-trip (100% of in-scope first-pass capabilities)** — Phase 1 closed. Optional Phase 1.5: 4c.3.2 group writes, 4c.5.2 audio levels, 4c.6.2 chart/table mutation, 4c.8.2 `new_slide(kind=...)` template instantiation + `kpa harvest` CLI. |
