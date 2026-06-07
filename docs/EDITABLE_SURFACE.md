# KPA Editable Surface — Total Coverage

**Status:** SCOPE EXPANSION captured 2026-06-07 08:28 PDT
**Captain directive:** "Our programmatic editing capabilities extend to all
the aspects embedded in the presentation, including, but not limited to,
slide and slide element animations and their parameters, graphical style
settings for every element including things like font sizes, justification,
spacing, color, shadows, opacity, graphical masks and shapes and scaling,
videos and their settings such as looping and audio levels…. **all editable
elements in the file structure.**"

This document maps the directive to the actual `.key` file structure
empirically observed across SVEF + NCI reference decks (180 slides,
31,460 archive instances, 88 distinct protobuf types).

## Headline numbers (empirical, SVEF + NCI)

| Surface | Distinct protobuf types | Total instances |
|---|---|---|
| **Style** (paragraph, character, shape, list, drop-cap, etc.) | 28 | 1,956 |
| **Animation / Build** | 2 | 52 |
| **Media** (movies, live video, audio/soundtrack) | 5 | 75 |
| **Text storage + layout** | core 4 | 5,901 |
| **Geometry / masks / images** | core 5 | 845 |
| **Charts** (series, axis, legend, drawables) | 10 | 154 |
| **Tables** (style network, presets, strokes, cell style) | 7 | 380 |
| **Document-level** (Slide, SlideNode, SlideStyle, MotionBg) | 6 | 1,025 |

**Total editable surface: 88 distinct `_pbtype` values, 31,460 instances.**

That's the ceiling. KPA's job: make every one of them addressable through
the Python API.

## Coverage map — what we own vs what's left

### ✅ Phase 1 Step 4a/4b (DONE)
- Load + save (lossless round-trip, F1 ✓)
- TextBlock: get/set text, position, size, move
- Image: position, size, move
- Coordinate semantics (pct / pt / px) ✓

### 🟡 Phase 1 Step 4c (this week — SCOPE EXPANSION lands here)
The mutation API expands to cover **every editable element**:

| Capability | Protobuf types involved | API surface |
|---|---|---|
| **Text styling** | `TSWP.ParagraphStyleArchive`, `TSWP.CharacterStyleArchive`, `TSWP.ListStyleArchive`, `TSWP.DropCapStyleArchive` | `TextBlock.font_name`, `.font_size`, `.font_weight`, `.italic`, `.underline`, `.color`, `.alignment`, `.line_spacing`, `.first_line_indent`, `.bullet_style`, `.list_level` |
| **Shape styling** | `TSWP.ShapeStyleArchive`, `TSD.StrokeLayerArchive` | `Shape.fill`, `.stroke`, `.stroke_width`, `.stroke_color`, `.stroke_dash`, `.corner_radius` |
| **Color** | RGBA dicts inside fills/strokes/text | `Color(r, g, b, a)` value type + named-theme-color resolver |
| **Shadow** | shadow sub-dicts on shape archives | `.shadow = Shadow(color, offset_x, offset_y, blur, opacity)` |
| **Opacity** | `opacity` floats on drawables | `.opacity` (0.0–1.0) |
| **Mask** | `TSD.MaskArchive` (172 instances) | `Image.mask`, `Image.crop_to_mask(shape)` |
| **Image scaling / fit** | scale + fitType in image archive | `Image.fit_mode = "stretch" / "fill" / "fit"`, `Image.scale = 1.5` |
| **Rotation** | `geometry.angle` (already in tree) | `.angle = 15` (degrees) |
| **Flip** | `pathsource.horizontalFlip`, `verticalFlip` | `.flip_horizontal()`, `.flip_vertical()` |
| **Z-order** | `KN.SlideArchive.drawablesZOrder` | `Slide.bring_to_front(elem)`, `.send_to_back()`, `.reorder([...])` |
| **Group / ungroup** | `TSD.GroupArchive` (46) | `Slide.group([a, b, c])`, `Group.ungroup()` |
| **Animations / builds (entry, exit, action)** | `KN.BuildArchive` (26), `KN.BuildChunkArchive` (26) | `.entrance(effect="fade", duration=0.5, delay=0)`, `.exit(...)`, `.emphasis(...)`, `.build_order = N` |
| **Slide transitions** | transition dict on `KN.SlideArchive` (already 1× per slide) | `Slide.transition = Transition(type="dissolve", duration=1.0)` |
| **Movies / videos** | `TSD.MovieArchive` (23), `TSD.MediaStyleArchive` (46) | `Video.loop`, `.start_time`, `.end_time`, `.autoplay`, `.audio_level`, `.poster_frame_time` |
| **Audio / soundtrack** | `KN.Soundtrack` (2) | `Deck.soundtrack = Soundtrack(asset, loop=True, volume=0.7)` |
| **Live video** | `KN.LiveVideoSource`, `KN.LiveVideoSourceCollection` | `LiveVideo` proxy (rare; supported but low priority) |
| **Motion background** | `KN.MotionBackgroundStyleArchive` (36) | `Slide.motion_background = MotionBg(asset, ...)` |
| **Charts** | 10 chart-related types | `Chart.series[i].color`, `.axis.labels`, `.legend.visible`, `.style` — full chart styling. Step 5 lands the chart object model; 4c lands chart-styling pass-through. |
| **Tables** | 7 table types | `Table.cell(r, c).set_value()`, `.set_style()`, `.merge(r1, c1, r2, c2)`, etc. (Step 5 fully; 4c lands cell-value + cell-style pass-through.) |
| **Notes** | `KN.NoteArchive` (146 — speaker notes) | `Slide.notes` (get/set string) |
| **Guides** | `TSD.GuideStorageArchive` (180) | `Slide.guides.add()`, `.remove()`, `.list()` |
| **Master / theme** | `KN.SlideStyleArchive` (36), `TSS.StylesheetArchive` (2) | `Deck.theme`, `Deck.masters`, `Deck.apply_theme(other_deck)` |

### 🟢 Phase 1 Step 4d
- CLI DSL covering the full mutation API
- F2/F2b/F2c gates green end-to-end
- Documentation

### 🟢 Phase 1 Step 5
- Native editable charts (full TSCH object model)
- Native editable tables (full TST object model)

### 🟢 Phase 1 Step 6
- Design-language layer (theme-binding, brand validator, brand-asset grovel)

## Engineering strategy

The directive expands surface area but does NOT change the engineering
strategy: **template-anchored mutation over the unpacked YAML tree.**
Every protobuf type listed above is already represented in the YAML
tree after `kpa.Deck.from_template()`. The mutation API is just a
typed, ergonomic skin over the YAML dictionary.

### Coverage discipline

For every category in the table above, KPA ships:

1. **A read accessor** (e.g. `TextBlock.font_size`) — returns the
   current value, resolved through theme inheritance when needed.
2. **A write accessor** (e.g. `TextBlock.font_size = 36`) — writes
   the value into the YAML tree, marks the slide dirty.
3. **A round-trip test** — load → mutate → save → reopen → confirm
   the mutation persisted with the expected value.
4. **A Keynote.app visual check** — once per category, manually open
   the saved deck and confirm Keynote renders the mutation correctly.

When a category is partially supported (e.g. charts pass-through in
4c but full object model in Step 5), the docs say so explicitly and
the API exposes a `raw_dict` escape hatch so agents can still write
the underlying field directly.

### Escape hatch (always available)

For categories not yet wrapped in a typed API:

```python
slide.raw_archive(id_or_pbtype)["someField"] = value
slide._mark_dirty()
```

This is the universal back-door. If KPA hasn't typed it yet, the agent
can still reach in and mutate the YAML tree. Mark-dirty + save flushes
the change.

### Test coverage gate

For Step 4c to be GREEN: every capability in the "Step 4c" table row
above must have at least one round-trip test and one visual smoke
verification on a real `.key` opened in Keynote 14.5.

## Coverage tracking

Coverage is tracked in `docs/COVERAGE.md` (lives at HEAD of Step 4c).
Each capability has a status: `unmapped` / `prototyped` /
`round-trip` / `visual-verified` / `production`.

Target before Phase 1 release (PyPI v0.1): all Step 4c capabilities at
`round-trip` minimum; all common-path ones at `visual-verified`.

## Out of scope (Phase 1)

These are real editable surfaces but pushed to later phases:
- **Live collaboration cursors / lock states** — only matters in iCloud
- **Presenter notes drawing** — handwriting strokes, low priority
- **3D objects** — Keynote 13+, rare in real decks
- **Complex animation paths** (motion paths beyond canned effects) —
  Step 5b, optional
- **Reactions / live captions** — runtime-only, no `.key` representation

Everything else is in scope per Captain 2026-06-07 08:28 PDT.
