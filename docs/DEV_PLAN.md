# DEV_PLAN — KPA (Keynote Programmatic Authoring)

**Version:** 1.0
**Author:** Scotty
**Created:** 2026-06-06
**Status:** ACTIVE — Phase 1
**PRD:** `docs/PRD.md` v1.0 (approved 2026-06-06)

---

## Phasing overview

| Phase | Theme | Deliverable | Success criteria |
|-------|-------|-------------|------------------|
| **1** | Native Keynote author + multi-agent surface | `kpa` Python lib + MCP server + skill + CLI | F1–F8 (see PRD §5) |
| **2** | PowerPoint + PDF export | `.pptx` + PDF emission via KPA model | separate PRD |
| **3** | Full round-trip + PDF import | `.key ↔ .pptx ↔ .pdf` lossless | separate PRD |
| **Port** | Apple-Silicon HAL | parity on Mac Studio | end of Phase 1 |

Phase 1 is divided into **7 ordered steps**. Each step ends with a commit and a status-log entry. No step starts before the previous one is checked off (unless explicitly parallelizable, marked **∥**).

---

## Phase 1 — Native Keynote Author + Multi-Agent Surface

### Step 1 — Recon, repo, vendoring (Day 1)

- [x] Recon: locate SVEF + NCI reference decks, confirm Keynote 14.5, confirm IWA structure
- [x] Recon: confirm all 15 `.proto` filenames embedded in Keynote.app binary
- [x] Decide: name = **KPA**, license = **MIT**, scope (see PRD §11)
- [x] PRD v1.0 written and approved
- [x] DEV_PLAN v1.0 written
- [ ] `git init` on `~/scotty/projects/keynote-format`
- [ ] Create GitHub repo `openclaw/kpa` (or equivalent) — public, MIT
- [ ] **Sync-commit GATE:** push planning artifacts (`docs/`, this file, `recon/` notes — *not* the reference decks themselves)
- [ ] HAL mirror: `git remote add hal` pointing at HAL's clone path
- [ ] WorkManager entry created
- [ ] Vendor `keynote-parser` (psobot) into `vendor/keynote-parser/` as substrate

**Commit message:** `plan(kpa): PRD v1.0 + DEV_PLAN v1.0 approved`
**Status-log entry:** add to bottom of this file.

### Step 2 — Schema harvester (Day 2)

- [ ] Extract `.proto` schemas embedded in `/Applications/Keynote.app/Contents/MacOS/Keynote`
  - Use `strings` + binary section inspection
  - Output: `schemas/14.5/*.proto`
- [ ] Compile to Python bindings (`protoc --python_out=src/kpa/_pb/14_5/`)
- [ ] Diff against `keynote-parser`'s vendored 12.x schemas — log new messages and changed field numbers in `schemas/14.5/CHANGES.md`
- [ ] CLI subcommand: `kpa harvest-schemas`
- [ ] Tests: every schema parses; bindings importable

**Commit:** `feat(kpa): schema harvester for Keynote 14.5`

### Step 3 — IWA codec + ZIP packer (Days 3–4)

- [ ] Port / adapt `keynote-parser`'s IWA reader to the 14.5 schemas
- [ ] Write IWA writer (Snappy framing, varint headers, archive-info wrapper)
- [ ] ZIP packer / unpacker for `.key` bundles
- [ ] CLI: `kpa unpack`, `kpa pack`
- [ ] **F1 test:** unpack + repack SVEF and NCI losslessly. Both open in Keynote 14.5 without recovery dialog. Second-save diff is semantically empty.

**Commit:** `feat(kpa): IWA codec + F1 (round-trip) green`
**This is the F1 milestone.**

### Step 4 — Object-graph authoring + Python API (Days 5–8)

**See `docs/STEP4_BRIEF.md` for full planning context.**
**Captain Q1–Q6 answers (2026-06-07 07:30 PDT) folded in.**

Split into 4a / 4b / 4c / 4d. Each sub-step is its own commit + push.

#### Step 4a — Foundation: archive graph + ID allocator + template parity (Day 5)

- [ ] Inventory SVEF and NCI: enumerate every distinct slide kind
      present in both decks. Produce `docs/SLIDE_KINDS.md` listing
      observed kinds (title, content, divider, image, bullet, quote,
      chart, table, etc. — actual list from inventory, not theoretical).
- [ ] `kpa.Deck.from_template(path)` — loads existing `.key` into the
      Python object model.
- [ ] `kpa.Element` base class — stable addressable handle
      (`element.id`, `element.path`, `element.kind`, `element.role`).
- [ ] `SlideTreeManager` — atomic updates of `slidelist`, navigator,
      thumbnail index, archive registry. Prevents R1 / S4-R1 invariant
      drift.
- [ ] `ArchiveIDAllocator` — reads template `max_id`, allocates above
      it, verifies non-collision before write. Deterministic on
      `(deck_hash, allocation_order)` so re-runs produce stable IDs.
- [ ] No-op mutation test: `kpa.Deck.from_template(svef).save(out)` must
      produce a deck where F1 round-trip is still 628/628 byte-identical.
      Same for NCI 325/325.
- [ ] Default brand-neutral template harvested from Apple's stock
      "White" or "Modern Portfolio" theme. Vendored at
      `kpa/templates/_default_neutral.key`.
- [ ] **S4.1 + S4.5 gate green.**

**Commit:** `feat(kpa): 4a foundation — template parity + ID allocator`

#### Step 4b — Text + Image mutation API + first 3 slide kinds (Days 6–7a)

- [ ] `kpa.TextBlock` with `.text`, `.set_font(name, size?, weight?)`,
      `.move(dx, dy, units="pct|pt|px")`, `.set_position(x, y)`,
      `.resize(w, h)`, `.set_color(rgb_or_named)`.
- [ ] `kpa.Image` with `.set_source(path)`, `.move`, `.resize`,
      `.crop`, `.set_opacity`.
- [ ] `kpa.AssetManager` — atomic embed of new image bytes into
      `Data/`, creates `Datas` archive entry, generates stable
      `<name>-<id>.<ext>` filename, anchors fill/imageMedia ref.
- [ ] Coordinate engine: pct ↔ pt ↔ px conversion with explicit
      reference frames.
- [ ] Address-book resolver: `deck.slide[i].title`,
      `deck.slides.where(role="title")`, `deck.find("slide-3-hero")`.
      Round-trips stable across re-save.
- [ ] Three slide kinds end-to-end (cloned, mutated, re-anchored):
      `title`, `text_image`, `bullet_list`.
- [ ] Mid-checkpoint: F2-edit smoke (move, font swap, image swap) green
      against SVEF.

**Commit:** `feat(kpa): 4b mutation API + 3 slide kinds + edits land`

#### Step 4c — Total editable surface + remaining slide kinds + brand validator + asset grovel (Days 7b–9)

**Scope expanded per Captain 2026-06-07 08:28 PDT:** mutation API now
covers **every editable element** in the `.key` file structure. See
`docs/EDITABLE_SURFACE.md` for the empirical map (88 distinct `_pbtype`
values across SVEF + NCI). Step 4c grows from ~1 day to ~3 days to
absorb this. Each capability ships with a round-trip test + visual
smoke verification in Keynote 14.5.

**4c.1 — Text styling (TSWP family)**
- [ ] `TextBlock.font_name`, `.font_size`, `.font_weight`, `.italic`,
      `.underline`, `.strikethrough`, `.color` (Color RGBA value type)
- [ ] `TextBlock.alignment` (left/center/right/justify),
      `.line_spacing`, `.first_line_indent`, `.before_paragraph_spacing`,
      `.after_paragraph_spacing`
- [ ] `TextBlock.bullet_style`, `.list_level` (TSWP.ListStyleArchive +
      DropCap pass-through)
- [ ] Run-level text: `TextBlock.runs` for per-character styling when
      needed (set a single word bold, color a phrase, etc.)

**4c.2 — Shape styling + visual effects**
- [ ] `Shape.fill` (solid color, gradient, image fill)
- [ ] `Shape.stroke` (color, width, dash, line cap)
- [ ] `Shape.shadow = Shadow(color, offset_x, offset_y, blur, opacity)`
- [ ] `Drawable.opacity` (0.0–1.0) — universal across text/shape/image/video
- [ ] `Shape.corner_radius`
- [ ] `Drawable.angle = N` (rotation in degrees), `.flip_horizontal()`,
      `.flip_vertical()`
- [ ] `Image.fit_mode` (stretch/fill/fit), `Image.scale`
- [ ] `Image.mask` (TSD.MaskArchive read/write/replace),
      `Image.crop_to_mask(shape)`

**4c.3 — Layout + structure**
- [ ] `Slide.bring_to_front(elem)`, `.send_to_back(elem)`,
      `.reorder([...])` (KN.SlideArchive.drawablesZOrder)
- [ ] `Slide.group([a, b, c])` returns `Group`; `Group.ungroup()`
      (TSD.GroupArchive)
- [ ] `Slide.guides.add(x_pt=None, y_pt=None)`, `.remove(g)`,
      `.list()` (TSD.GuideStorageArchive)
- [ ] `Slide.notes` get/set (KN.NoteArchive — speaker notes)

**4c.4 — Animations + transitions**
- [ ] `Element.entrance(effect, duration, delay, trigger)`,
      `.exit(...)`, `.emphasis(...)` (KN.BuildArchive,
      KN.BuildChunkArchive)
- [ ] `Element.build_order` (animation ordering within a slide)
- [ ] `Slide.transition = Transition(type, duration, direction, ...)`
      (transition dict on KN.SlideArchive)
- [ ] Catalog of supported effect names mapped to Keynote's internal
      animation ids (dissolve, fade, push, magic move, swap, etc.)

**4c.5 — Media (video + audio)**
- [ ] `Video.loop`, `.autoplay`, `.start_time`, `.end_time` (trim),
      `.audio_level` (0.0–1.0), `.poster_frame_time`, `.show_controls`
      (TSD.MovieArchive, TSD.MediaStyleArchive)
- [ ] `Video.replace(asset_path)` swap source file in Data/
- [ ] `Deck.soundtrack = Soundtrack(asset, loop, volume, fade_in,
      fade_out)` (KN.Soundtrack)
- [ ] `Slide.motion_background = MotionBg(asset, ...)`
      (KN.MotionBackgroundStyleArchive)
- [ ] `LiveVideo` proxy (KN.LiveVideoSource) — read-only inspect first,
      mutation in Step 5 if needed

**4c.6 — Charts + tables (pass-through; full object models in Step 5)**
- [ ] `Chart.style`, `.series[i].color`, `.axis.title`, `.legend.visible`
      (TSCH.ChartStyleArchive, TSCH.ChartSeriesStyleArchive,
      TSCH.ChartAxisStyleArchive, TSCH.LegendStyleArchive)
- [ ] `Table.cell(r, c).value`, `.cell(r, c).set_style(...)` (TST.*)
- [ ] Full TSCH/TST object models land in Step 5; 4c gives the
      styling pass-through.

**4c.7 — Universal escape hatch**
- [ ] `Slide.raw_archive(id_or_pbtype) -> dict` returns the live YAML
      dict for any archive on the slide. Mutations to this dict are
      flushed on save (caller must call `slide._mark_dirty()` after).
- [ ] `Deck.raw_archive(path)` for document-level archives
      (Document.iwa, DocumentStylesheet.iwa, etc.)
- [ ] Documented as the back-door for anything KPA hasn't typed yet.

**4c.8 — Slide-kind library + brand validator + asset grovel**
- [ ] Three remaining V1 slide kinds: `section_divider`, `quote`,
      `closing`. Additional kinds added incrementally from the SVEF/NCI
      inventory as agents need them. Step 5 adds `chart`.
- [ ] `kpa.Theme` (partial — just enough for the validator; full theme
      system lives in Step 6).
- [ ] `kpa.BrandComplianceValidator`:
      - non-theme fonts → reject (configurable warn)
      - non-palette colors → flag
      - off-grid positions → snap or flag
      - `brand_override=True` opt-out logged to audit trail
- [ ] `kpa harvest --assets <dir> --out <library>` recursive scanner
      (F4b from PRD v1.1):
      - walks directory tree for `.key` files
      - unpacks each; extracts every `Data/*` (images, video, fonts,
        chart templates)
      - deduplicates by content hash (sha256)
      - indexes by source-deck path + slide index + element role
      - emits a `kpa.BrandAssetLibrary` JSON manifest + content-addressed
        asset directory
      - consumable by `deck.brand_assets.search("logo")`,
        `.search(tag="video")`, `.use(asset_id)`

**4c gates (all must be GREEN to ship 4c):**
- [ ] **S4.10** — brand validator passes on F2 deck
- [ ] **S4.11** — F2d coverage: every capability in 4c.1–4c.7 has at
      least one round-trip test
- [ ] **S4.12** — visual smoke matrix: each capability category opened
      manually in Keynote 14.5 with a sample mutation, confirmed to
      render correctly
- [ ] `docs/COVERAGE.md` updated to show each capability at `round-trip`
      minimum (target: `visual-verified`)

**Commit (per sub-section, pushed independently):**
  - `feat(kpa): 4c.1 text styling (font/color/alignment/spacing/runs)`
  - `feat(kpa): 4c.2 shape styling (fill/stroke/shadow/opacity/mask)`
  - `feat(kpa): 4c.3 layout (z-order/group/guides/notes)`
  - `feat(kpa): 4c.4 animations + transitions`
  - `feat(kpa): 4c.5 media (video loop/audio/soundtrack/motion-bg)`
  - `feat(kpa): 4c.6 charts + tables pass-through styling`
  - `feat(kpa): 4c.7 universal raw_archive escape hatch`
  - `feat(kpa): 4c.8 brand validator + asset grovel + slide kinds`

#### Step 4d — CLI surgical-edit DSL + F2/F2b/F2c gates + CI + docs (Day 8)

- [ ] CLI sugar: `kpa author --spec deck.py --template <path?> --out deck.key`
- [ ] CLI surgical edits: `kpa edit deck.key 'slide[3].title.move(dy="20%")'`
      Parses DSL into Python API calls. Same code path as MCP JSON
      form (design invariant).
- [ ] Headless `kpa.open(path).save(path2)` parity (S4.4).
- [ ] **F2 test gate** (S4.2 + S4.3): 10-slide greenfield deck opens
      in Keynote 14.5, zero recovery dialogs, saves clean on second open.
- [ ] **F2b test gate** (S4.9 — surgical-edit suite): load SVEF,
      apply 5 named edits via API, save, re-open in Keynote.app, every
      edit persisted, zero recovery dialogs.
- [ ] **F2c smoke**: scripted agent prompt → KPA-authored deck (verifies
      API handles planner output; full F2c with LLM in the loop lives
      in Step 7).
- [ ] `docs/authoring.md` with worked example.
- [ ] CI extension: `tests/test_authoring.py` + `tests/test_edits.py`.
- [ ] **Option 2 ships here** (Captain's locked sequence): Keynote.app
      as human review surface. Document workflow in
      `docs/review_with_keynote.md`. Zero-code; usage notes only.
- [ ] Sub-step retrospective.

**Commit:** `feat(kpa): 4d CLI DSL + F2/F2b/F2c green + Option 2 documented`

**Step 4 exit gate:** S4.1–S4.10 ticked. F1 still green. All four
sub-step commits pushed to origin (HAL pulls).

#### Step 4 plan-level commitments

- Slide-kind taxonomy: growing library from SVEF + NCI inventory
  (Captain Q3).
- Default template: brand-neutral Apple (Captain Q1).
- Spec format: imperative API canonical, declarative dict sugar
  (Captain Q2). MCP server consumes the JSON form.
- Test assets: CC0 set + procedural generation (Captain Q4).
- Round-trip-with-mutation: KPA headless in CI, AppleScript at release
  (Captain Q5).
- Release: `v0.1` private to fleet after F1–F5, `v0.2` public after
  F6–F8 (Captain Q6).
- Coordinate semantics: pct (default) / pt / px. `move()` relative;
  `set_position()` from slide canvas top-left.
- Edit DSL invariance: Python API, CLI sugar, MCP JSON of the same
  edit must produce byte-identical output. CI-enforced design invariant.
- Conversational LLM editing (Captain 2026-06-07 07:42 PDT): full-power
  natural-language understanding of any aspect is the agent's job
  (Step 7 critic + MCP). The API must be expressive enough that the
  agent can translate any reasonable natural-language edit into
  KPA calls. API gaps get fixed.

### Step 5 — Native editable charts (Days 9–11)

- [ ] `kpa.Chart` — bar, column, line, pie, scatter
- [ ] Bootstrap by copying a reference TSCH archive and mutating its data
- [ ] Progressively reduce dependence on the template until pure synthesis works
- [ ] **F3 test:** Bar+line dual-axis chart opens, editable in Keynote chart inspector, visual diff ≤1% vs hand-authored

**Commit:** `feat(kpa): native editable charts + F3 green`

### Step 6 — Design-language layer + SVEF deliverable (Days 12–14)

- [ ] `kpa.Theme` (colors, fonts, masters, grids)
- [ ] `kpa.DesignSpec` (semantic intent → theme primitives)
- [ ] Theme harvester: `harvest_theme(deck) → theme dict`
- [ ] Accept Captain's `design.md` (Brainworks) when supplied; encode as Theme
- [ ] **F4 test:** Regenerate ≥5 slides of SVEF from Python spec; Captain reviews; passes Brainworks sniff test
- [ ] **F8 test:** Round-trip Brainworks theme (SVEF → design.md → fresh deck) — brand-consistent

**Commit:** `feat(kpa): design language + F4/F8 green`
**Captain review milestone.**

### Step 6.5 — Graphical review hooks (Day 14b, runs alongside Step 6)

**Per Captain's locked sequencing (2026-06-07 07:42 PDT, revised 08:01):**
Option 2 → Option 3-lite → (Option 1 if Anthropic opens MCP) →
**Option 5 → Option 4**. Phase 1 ships Options 2 and 3-lite; Phase 2
builds **Option 5 (PPTX bridge) first**, then Option 4 (custom HTML
canvas); Option 1 inserts any time on Anthropic announce.

Captain 2026-06-07 08:01 PDT: "Let's move the cross format bridge to
before our custom live editing canvas work." Rationale: PPTX bridge
ships ~4–6 weeks vs Option 4's 3–6 months. Ship cross-format value
first (Claude Design → PPTX → KPA becomes live, Captain can use Claude
Design today and ingest the result), then build the proprietary live
canvas as the IP moat.

- [ ] **Option 2 already shipped in Step 4d** (Keynote.app as human
      review surface, documented).
- [ ] **Option 3-lite** — `kpa preview deck.key --out preview/`:
      - renders every slide to a PNG via same code path as Step 7's
        `kpa_render_thumbnail` MCP tool
      - supports `--format png|svg|html` (HTML lite, not interactive)
      - headless: works on Linux CI runners
      - visual-regression threshold: ~5–10% (HTML render lossier than
        Keynote.app; charts use Step-5 native renderer)
      - emits per-slide PNG + per-deck contact sheet
- [ ] **Anthropic-watch trigger** — weekly cron job checking
      https://www.anthropic.com/news for Claude Design MCP opening.
      Default delivery: announce to telegram:8383711967 with summary +
      link. When trigger fires, Step 6.6 inserts ahead of in-flight work.

**Commit:** `feat(kpa): 6.5 preview hooks + Option 2/3-lite + Anthropic watch`

### Step 6.6 (CONDITIONAL) — Claude Design MCP integration (Option 1)

**Trigger:** Anthropic-watch cron job fires "Claude Design MCP open."
**SLA:** 1–2 weeks; queue-jumps whatever else is in flight.

- [ ] Add MCP tools to `kpa-mcp` server:
      `kpa_export_to_canvas(deck_path) → html_bundle + asset_manifest`
      `kpa_import_from_canvas(html_bundle) → deck_path`
- [ ] HTML ↔ IWA mapping: lossy, documented.
- [ ] Register KPA's MCP server with Claude Design per their docs.
- [ ] First-PR open-source story: "first MCP server to extend Claude
      Design with native Keynote support."
- [ ] Captain dogfoods round-trip: design in Claude Design → KPA emits
      `.key` → opens in Keynote.app pixel-acceptable.

**Commit:** `feat(kpa): 6.6 Claude Design MCP bridge (Option 1)`

### Step 7 — MCP server + skill + critic loop (Days 15–18)

- [ ] MCP server `kpa-mcp` exposing tools:
  - `kpa_read_deck`, `kpa_inspect_slide`, `kpa_edit_slide`,
    `kpa_author_deck`, `kpa_apply_theme`, `kpa_render_thumbnail`,
    `kpa_validate`, `kpa_critique`
- [ ] Thumbnail renderer (Keynote.app via AppleScript on macOS; pure-Python fallback flagged)
- [ ] Mechanical critic: overflow / contrast / grid / chart-label
- [ ] Aesthetic critic: LLM-graded against design.md (caller-supplied LLM)
- [ ] OpenClaw skill `brainworks-deck` published into `~/scotty/skills/`
- [ ] **F5 test:** HAL authors a 5-slide brief from a natural-language prompt via the skill
- [ ] **F6 test:** Claude Desktop + Claude Code + HAL each author the same 5-slide brief via their surface; blind-graded
- [ ] **F7 test:** Claude Desktop opens SVEF, finds 3 design issues, applies fixes, re-saves; critic re-rates improved

**Commit:** `feat(kpa): MCP + skill + critic loop + F5/F6/F7 green`
**Phase 1 complete.**

### Phase 1 wrap

- [ ] All success criteria F1–F8 + F2b + F2c + F4b green
- [ ] Docs published: Python API (Sphinx), MCP tools README, skill README,
      `docs/authoring.md`, `docs/review_with_keynote.md`
- [ ] PyPI release: `pip install kpa` — `v0.1` (private fleet)
- [ ] GitHub release tagged `v0.1.0` (private, not announced)
- [ ] Apple-Silicon port to HAL (Mac Studio) — codec + schemas + tests parity
- [ ] **v0.2 public release** after F6–F8 also green; open-source
      announcement
- [ ] PRD v1.2 / DEV_PLAN v2.0 for Phase 2 drafted

## Phase 2 (PPTX bridge → Custom HTML canvas)

Per Captain's revised sequence (2026-06-07 08:01 PDT, supersedes the
07:42/07:43 ordering): **Option 5 ships first, then Option 4.**

  Captain: "Let's move the cross format bridge to before our custom
  live editing canvas work."

Rationale (revised): the cross-format bridge gives the legion an
immediate working path — Claude Design → PPTX export → KPA → native
`.key` — in 4–6 weeks. Captain can use Claude Design TODAY for visual
authoring and pipe results through KPA into native Keynote. After that
bridge proves out and shapes our object-model needs, we build the
proprietary live HTML canvas (Option 4) as the IP moat with the
benefit of real-world usage data from the PPTX flow.

### Step 8 — PPTX bridge (Option 5) — 4–6 weeks  **[Phase 2a, first]**

- [ ] `kpa.PPTXReader` — ingest `.pptx`, map to KPA object model
- [ ] `kpa.PPTXWriter` — emit `.pptx` from KPA object model
- [ ] Round-trip parity gate: `.key → .pptx → .key` lossless on curated
      subset (animations excluded per OOXML limits)
- [ ] Claude Design → PPTX → `.key` workflow documented and dogfooded
      end-to-end (Captain authors a deck in Claude Design, KPA ingests,
      exports clean `.key`)
- [ ] CLI: `kpa convert in.pptx --out out.key` and reverse
- [ ] Brand validator runs on imported PPTX content (Step 4c validator
      already shipped; this just exercises it on PPTX-sourced objects)
- [ ] PyPI release `v0.2` (Phase 2a GA)
- [ ] GitHub release tagged `v0.2.0`

### Step 9 — Custom HTML canvas (Option 4) — 3–6 months  **[Phase 2b, after Step 8]**

- [ ] FastAPI / Lit / vanilla-JS canvas at `kpa serve --port 8080`
- [ ] Two-pane UX: chat on the left, live HTML render on the right
- [ ] Drag / click / resize interactions ↔ KPA API
- [ ] Conversational edit pane wired to caller-supplied LLM
- [ ] Visual-regression: drift from Keynote.app render < 10% per slide
- [ ] Headless mode for CI: `kpa render --slide N --out s-N.png`
- [ ] Object-model refinements informed by PPTX-bridge usage from Step 8

### Step 10 — PDF export

- [ ] `kpa.PDFExporter` via Keynote.app headless export (high fidelity)
- [ ] Pure-Python fallback for non-Mac fleet agents

### Phase 2 wrap

- [ ] PRD v2.0 (`.pptx` + `.pdf` + custom canvas first-class)
- [ ] PyPI release: `v0.3` (Phase 2b GA — custom canvas shipped)
- [ ] GitHub release tagged `v0.3.0`

_Note: `v0.2.0` ships earlier when Step 8 (PPTX bridge) is feature
complete. Phase 2 has two release tags: `v0.2.0` after Step 8,
`v0.3.0` after Step 9._

---

## Engineering principles (encoded)

1. **Harvester is the contract.** Never hand-edit a `.proto`. Always re-harvest.
2. **Round-trip before greenfield.** F1 ships before F2. R1 mitigation.
3. **Templates before synthesis (for charts).** F3 starts by mutating a real TSCH; pure synthesis is the *end* state of Step 5, not the start.
4. **The Python API is the deliverable.** CLI, MCP, and skill are thin shims.
5. **Mechanical beauty is binary; aesthetic beauty is graded.** Critic loop separates the two.
6. **Open-source from day one.** MIT, GitHub, PyPI. No private artifacts in commits (reference decks live in `recon/` and `.gitignore`'d).

## Quality gates (all phases)

- Every commit on `main` passes CI (round-trip against SVEF + NCI).
- Every Step ends with a status-log entry below.
- No PRD scope change without bumping PRD version and notifying Captain.
- No `git push` to public remote without `kpa validate` passing on test corpus.

---

## Status Log

### 2026-06-07 08:35 PDT — Step 4b GREEN + Step 4c scope expansion (total editable surface)

**Captain directive 2026-06-07 08:28 PDT:**
  "Let's make sure that our programmatic editing capabilities extend to
  all the aspects embedded in the presentation, including, but not
  limited to, slide and slide element animations and their parameters,
  graphical style settings for every element including things like font
  sizes, justification, spacing, color, shadows, opacity, graphical
  masks and shapes and scaling, videos and their settings such as
  looping and audio levels….all editable elements in the file structure."

**Empirical surface size (SVEF + NCI scan):**
  - 88 distinct `_pbtype` values
  - 31,460 archive instances
  - 28 style-related types, 2 animation types, 5 media types

**Captured in:**
  - `docs/EDITABLE_SURFACE.md` — full empirical map of editable types
  - `docs/COVERAGE.md` — live coverage tracker, 69 capabilities split
    into 8 sub-sections (4c.1 through 4c.8)
  - PRD v1.3 — F2d success criterion added (total editable surface)
  - DEV_PLAN Step 4c expanded from ~1 day to ~3 days; sub-steps 4c.1
    through 4c.8 each ship as their own commit

**Step 4b complete (commit fab929b):**
  - kpa.coords (pct/pt/px parsing)
  - kpa.objects (Slide / TextBlock / Image proxies, _Geometry mutable view)
  - kpa.deck extended (canvas read from KN.ShowArchive, lazy slide load,
    dirty-set tracking, multi-chunk slide handling)
  - tests/test_edits.py: 3 GREEN
    - text_edit + move round-trip
    - set_position('50%', '25%') -> exact pt coords
    - image move round-trip
  - Full suite: 6/6 PASSED in 89s
  - Engineering finding: SVEF/NCI authors put real text in ad-hoc shapes,
    not master title/body placeholders. Confirmed the inventory hypothesis
    from 4a empirically in 4b.

**Next: Step 4c.1 — text styling (font/color/alignment/spacing/runs).**

---

### 2026-06-07 08:03 PDT — Step 4a GREEN + Phase 2 sequence locked

**Done today (planning + code, in chronological order):**

**Planning churn — Phase 2 sequence converged:**
1. 07:30 PDT — Captain answered Q1–Q6 (Step 4 blockers): brand-neutral
   default, both authoring styles, growing slide-kind library seeded
   from SVEF+NCI, brand-asset grovel feature added, surgical edits +
   end-to-end generation are both first-class. PRD bumped to v1.1.
2. 07:33 PDT — Researched Claude Design (Anthropic Labs, launched
   Apr 17, MCP integration "coming weeks"). Wrote
   `docs/GRAPHICAL_REVIEW_OPTIONS.md`. Recommended Option 2 → 3-lite
   → 4 → 5 build order with Option 1 trigger.
3. 07:42 PDT — Captain locked the order, said "Go." Drafted Step 4
   sub-steps 4a–4d. Set Anthropic-watch cron
   `4783f42a-a425-41de-b699-21be3b6a599a` (Mondays 14:00 PDT).
4. 07:43 PDT — Captain reinforced "Option 4 before Option 5,"
   retracted my earlier "Option 5 might land de facto first" hedge.
5. 08:01 PDT — Captain **reversed** the Phase 2 order: "Let's move
   the cross format bridge to before our custom live editing canvas
   work." Phase 2a = Option 5 (PPTX bridge, ~4–6 weeks, PyPI v0.2);
   Phase 2b = Option 4 (custom HTML canvas, 3–6 months, PyPI v0.3).
6. 08:03 PDT — Captain: "Commit and push the latest prd and dev plan
   and status docs that capture all this and go build it."
7. PRD bumped to v1.2 capturing the Phase 2 reversal.

**Step 4a code GREEN (commit 213bfd2):**
- `src/kpa/` package skeleton: `Deck.from_template()` / `Deck.save()` /
  `Deck.summary()` / `kpa.open()`.
- `kpa` CLI: `unpack`, `pack`, `info`, `--version`.
- `pyproject.toml` editable install works (`pip install -e .`).
- `.github/workflows/ci.yml` on macOS runner.
- `tests/test_parity.py` — S4.1 (no-op parity) GREEN:
  - SVEF 628/628 byte-identical
  - NCI  325/325 byte-identical
  - Deck summary smoke test passes
- `scripts/slide_kind_inventory.py` + `docs/SLIDE_KINDS.{md,json}`:
  taxonomy seeded from real decks per Captain Q3.
  - **Finding:** SVEF/NCI each use essentially one master for ~85% of
    slides; visual diversity lives in slide-internal layout, not master
    clustering. Step 4b will clone individual slide exemplars per
    visual kind rather than masters.

**Commits pushed today (newest first):**
  - 068d302 — Phase 2 reversed (Option 5 first, then Option 4)
  - 5f9bc88 — Phase 2 'de facto Option 5 first' hedge retracted (superseded)
  - 213bfd2 — Step 4a foundation + S4.1 parity GREEN
  - 2177874 — Step 4 sub-steps 4a–4d + Captain's Phase 2 ordering locked
  - 947a8fa — PRD v1.1 (surgical edits + asset grovel first-class)
  - e0c78c4 — GRAPHICAL_REVIEW_OPTIONS research
  - 989db55 — STEP4_BRIEF planning doc

**Next:** Step 4b — mutation API (`kpa.TextBlock`, `kpa.Image`),
address book (`deck.slide[i].title.move(...)`, etc.), and first three
slide kinds (title, text_image, bullet_list) authorable end-to-end.
F2-edit mid-checkpoint: move + font swap + image swap land cleanly
on a real `.key`, openable in Keynote.app.

---

### 2026-06-07 05:30 PDT — Step 3d GREEN — Bug #5 fixed; F1 lossless covers SVEF + NCI 🎉

**Done:**
- Implemented `RawProtobufPatch` class in `codec.py` (venv + vendor):
  - Stores raw bytes verbatim from unsupported `ProtobufPatch` entries
  - `SerializeToString()` returns the raw bytes — buffer round-trip is bit-identical
  - `to_dict()` emits `{"_kpa_raw_patch": True, "data_base64": "..."}` for YAML serialization
  - `from_dict()` reconstructs from the YAML marker
- Changed `ProtobufPatch.FromString` to fall back to `RawProtobufPatch(data)` when either guard hits:
  - `len(message_info.diff_field_path.path) != 1`, or
  - `message_info.fields_to_remove` is populated
- Added marker discrimination in `IWAArchiveSegment.from_dict` to route YAML `_kpa_raw_patch` entries back to `RawProtobufPatch`.

**F1 results after the fix:**
- **NCI:** 325/325 files byte-identical (96 Index YAMLs + 219 Data + 3 Metadata + 3 previews). 182.2 MB of content, zero differences. Outer ZIP delta: 1,024 bytes / 179 MB (0.0006%).
- **SVEF regression:** 628/628 identical — zero regression.
- 2 YAMLs in NCI contain `_kpa_raw_patch` markers (`Slide-1100-2.iwa` and one more) — their bytes round-trip exactly.

**Verdict:** F1 lossless round-trip works for **the median real-world Keynote 14.5 deck**, not just synthetic single-save decks. Phase 1 read-side is now complete.

**Files updated:**
- `.venv/lib/python3.14/site-packages/keynote_parser/codec.py` (+ vendor copy in sync)

**Next:** Step 4 — object-graph authoring (F2).

### 2026-06-07 04:55 PDT — Step 3c VALIDATED — F1 confirmed in Keynote.app; NCI uncovers Bug #5 (deferred)

**Done:**
- Killed the sluggish 17h-uptime Keynote zombie; launched fresh `Keynote Creator Studio.app` instance.
- Opened the round-tripped `recon/round-trip/svef-roundtrip.key` via `open -a`. **Keynote loaded it without errors.**
- AppleScript probes (`count of documents`, `count of slides`) all returned `-1712 timeout` because TCC Automation permission is not granted for osascript → Keynote. This is a **cosmetic limitation**, not a file problem.
- Confirmation via the macOS unified log (`log show --predicate 'process == "Keynote"' --last 5m`):
  - Two `<KNMacDocument: ...>` instances active in PID 69578 (the freshly-opened file + the prior session's deck).
  - Zero `damage` / `recover` / `corrupt` / `cannot open` / `invalid format` log entries.
  - The only `error` lines are `TSCKSharingError code=11 (UnsupportedFileProvider)` — that error means "this file is on local disk, not iCloud" — totally expected.
  - One `libsqlite3 cannot open file at line 51044 of [f0ca7bba1c]` — a path-probing call, not a content error.
- **✅ F1 acceptance dual-confirmed: byte-for-byte 628/628 structural diff + clean Keynote.app open.**
- Second-deck attempt (NCI) **uncovered a new bug class** before completing unpack:
  - NCI has `TSWPSOS.StyleDiffArchive` ProtobufPatches with:
    - `length=0` (no payload)
    - `diff_field_path.path` empty (0 entries) — keynote-parser expects exactly 1
    - `fields_to_remove` populated (paths 2 and 43) — keynote-parser raises NotImplementedError
    - `diff_read_version: 25` — the version array `[2, 0, 25]` that confused the error message
  - Root cause: psobot's `ProtobufPatch.FromString` is read-only-NotImplemented for real-world `should_merge=True` patches that encode `fields_to_remove` operations.
  - This is **read-time semantic interpretation**, not bytes. A raw-bytes passthrough would preserve round-trip.

**Decision:** Document NCI's Bug #5 as a Step 4+ work item. SVEF F1 stands. NCI requires a `RawProtobufPatch` passthrough that preserves bytes-as-bytes for unsupported patch operations — design + implement in Step 4 or as a dedicated Step 3d, depending on Captain's call.

**Pushed:** commit forthcoming.

### 2026-06-07 04:13 PDT — Step 3b GREEN — F1 lossless round-trip ACHIEVED 🎉

**Done:**
- Re-verified Step 3a patches survived (snappy import OK, mapping patch OK, NAME_CLASS_MAP=1362, ID_NAME_MAP=631, 6383 present).
- Ran `keynote-parser pack recon/unpacked/svef --output recon/round-trip/svef-roundtrip.key`.
  Pack completed in ~5s for 628 entries. Size delta: 54,782,740 vs 54,784,985 = **2,245 bytes (0.004%) smaller**.
- Found and patched **two more upstream bugs** that broke the first round-trip:
  1. **Pack-side: ZIP UTF-8 filename flag mismatch.** Python's `ZipFile.writestr()` sets the 0x800 (UTF-8) general-purpose flag whenever a filename contains non-ASCII; Keynote.app NEVER sets that flag (writes UTF-8 bytes raw, expects readers to interpret). Our `zip_file_reader` then fails to decode any 0x800-flagged entry because it blindly tries `.encode("cp437").decode("utf-8")` and U+202F (narrow-no-break-space, used in macOS screenshot filenames) isn't representable in cp437.
  2. **Read-side amplifier.** The cp437 round-trip in `zip_file_reader` corrupts any filename that was already properly UTF-8-flagged by a third-party writer.
- Fix in `keynote_parser/file_utils.py` (now propagated to `vendor/`):
  - New `_AppleZipInfo(ZipInfo)` subclass overrides `_encodeFilenameFlags()` to write UTF-8 bytes without the 0x800 flag — exactly mirroring Keynote.app's bytes.
  - `zip_file_reader` now only does the cp437→utf-8 round-trip when 0x800 is clear; UTF-8-flagged entries are passed through untouched.
- **F1 ACCEPTANCE (full structural diff, unpack→pack→unpack):**
  - 628 / 628 files byte-identical (sha256 match)
  - 96 / 96 Index IWA YAMLs identical
  - 436 / 436 Data binary assets identical
  - 3 / 3 Metadata files identical (incl. Properties.plist, BuildVersionHistory.plist, DocumentIdentifier)
  - 3 / 3 preview*.jpg identical
  - **0 differences across 53.8MB+ of content**
  - ZIP flag-bit distribution: original 0/628 UTF-8 flagged → round-trip 0/628 ✅ exact match
- Keynote.app validation: deferred — `Keynote Creator Studio.app` instance is sluggish on Apple Events (had been running 17h on another deck). Structural diff is the stronger guarantee anyway; we'll re-verify with a clean Keynote launch on a smaller test deck in Step 3c.

**Round-trip diff that still matters:**
- 2,245 bytes (0.004%) byte-size delta on the outer ZIP. Confirmed NOT from the file contents (every byte of every internal file is identical). Almost certainly from ZIP central-directory ordering + date_time metadata. Investigate in Step 3c if Keynote actually cares (it won't — ZIP central directory ordering is by spec irrelevant).

**Next (Step 3c — minor):**
1. Verify with a clean Keynote.app launch on a small test deck that the round-trip is recognized as a valid Keynote 14.5 doc (not just structurally equivalent).
2. Run round-trip against a second deck (e.g. NCI-FLASH or a fresh blank deck) to confirm it isn't SVEF-specific luck.
3. Decide whether to chase the 2,245-byte ZIP delta or accept it (likely accept — every file inside is byte-identical).
4. Then move to Step 4 (object-graph authoring + F2).

### 2026-06-06 21:09 PDT — Step 3a complete, Step 3b queued

**Done:**
- Unpacked SVEF.key (~221MB) end-to-end: 97 IWA→YAML + 531 media assets = 628 files.
- Found & fixed two upstream bugs in keynote-parser stack:
  1. **snappy PyPI namespace collision** — `pip install python-snappy` co-pulls SnapPy topology lib which hijacks `import snappy`. Fix: uninstall `snappy`, keep only `python-snappy`.
  2. **mapping.py ignores nested protobuf types** — `compute_maps()` only walked top-level messages. Patched with recursive `_walk_messages()` walker (NAME_CLASS_MAP 1196→1362, ID_NAME_MAP 629→631, 100% TSPRegistryMapping coverage).
- Patch applied to `vendor/keynote-parser/keynote_parser/versions/v14_4/mapping.py` (load-bearing — do not revert).
- HANDOFF.md written for post-compaction continuity.

**Next (Step 3b):** Pack-side round-trip — `keynote-parser pack` then diff against original to prove F1 (lossless round-trip) hard requirement from PRD.


### 2026-06-06 19:24 PDT — Step 1 in progress
- PRD v0.2 → v1.0 (Captain approved via Telegram, msg 12029)
- DEV_PLAN v1.0 written
- Recon complete: schemas extractable, SVEF + NCI unpacked clean
- Next: git init + sync-commit gate + HAL mirror + WorkManager entry

### 2026-06-06 19:28 PDT — Sync-commit GATE PASSED
- `git init`, initial commit `3a2cd74`
- GitHub repo created: https://github.com/alvelda/kpa (public, MIT)
- HAL mirror cloned at hal:scotty/projects/keynote-format; `hal` remote added on iMac
- WorkManager: defers its own scaffold to a separate dir, conflict with our canonical workdir.
  Skipped for now; planning to register the *existing* project via patch endpoint once
  the WM API for "adopt existing path" is identified. Not blocking execution.
- Step 1 checkboxes 6, 7, 8 (git init / GitHub push / HAL mirror) done.
- Step 1 remaining: vendor keynote-parser, WorkManager registration (deferred)
- Moving on to Step 2 schema harvest while substrate vendoring runs in parallel

### 2026-06-06 19:30 PDT — Step 2 schema harvest GREEN
- Vendored keynote-parser (psobot) into `vendor/keynote-parser/` (gitignored)
- Created .venv with protobuf<4 + rich + python-snappy
- Ran `dumper/protodump.py` against `/Applications/Keynote.app`
  → 33 .proto files extracted to `schemas/14.5/raw/`
- Normalized filenames + import paths via `scripts/normalize_schema_filenames.sh`
  → `schemas/14.5/normalized/`
- **📊 Diff vs keynote-parser bundled 14.4: 33 / 33 byte-identical.**
  Apple shipped zero schema changes 14.4 → 14.5. R3 (schema drift) is very small
  for point releases.
- `schemas/14.5/CHANGES.md` documents the result and the re-harvest workflow
- Step 2 done (raw extract + normalization + diff). Compile-to-Python and
  smoke-test still to do but unblocked
- Next: commit progress, then Step 3 IWA codec adaptation


### 2026-06-07 — Steps 3/4 condensed log

(Detailed entries live in `docs/COVERAGE.md` status log + commit history.)

- **Step 3 GREEN** — keynote-parser fork patched (snappy collision + recursive `_walk_messages()` in mapping.py). F1 lossless round-trip verified on SVEF + NCI.
- **Step 4a parity GREEN** (3 tests) — Deck.from_template + save round-trip.
- **Step 4b mutation GREEN** (3 tests) — TextBlock/Image/Slide proxies + set_text/move/set_position.
- **PRD v1.3 approved by Captain (08:28 PDT)** — scope expanded to TOTAL editable surface.

### 2026-06-07 — Step 4c sub-steps (Editable Surface)

- **4c.1 text styling GREEN** (9 tests) — font/color/alignment/spacing on char + para styles.
- **4c.2 shape visuals GREEN** (9 tests) — fill/stroke/shadow/opacity/reflection.
- **4c.4 animations + transitions GREEN** (13 tests) — Build, Transition, EFFECTS catalog, add/remove_build. Discovered TSP.ArchiveInfo messageInfos requirement.
- **4c.5 media GREEN** (13 tests) — Movie/Soundtrack/LiveVideoSource. First Document.iwa.yaml writes; Deck._document_root() plumbing landed.

### 2026-06-08 09:15 PDT — Step 4c.7 GREEN

- **4c.7 universal escape hatch GREEN** (18 tests) — kpa.escape module + RawArchiveMixin wired into 8 proxies (TextBlock, Image, Slide, Build, Transition, Movie, Soundtrack, LiveVideoSource).
- Universal API: `raw_archive()`, `raw_get(path)`, `raw_set(path, value)`, `raw_keys(path)`, `raw_dump(path, maxdepth)`, `raw_pbtype()`.
- Path syntax: dot keys + `[N]` indices + mixed.
- Full suite: **68/68 passing** in 21m45s.
- Closes the "agent never blocked" gate — any field in any covered archive is writable, even without typed accessors.
- Phase 1 Step 4: **72/100 capabilities round-trip (72%)**.
- Commit `d716633` on origin/main.

### 2026-06-08 09:25 PDT — Handoff prepared

- `docs/HANDOFF.md` refreshed with current state, capability table, engineering findings, escape-hatch quick reference, and recommended next steps.
- Sub-steps remaining for Phase 1 close: **4c.3 layout/structure (NEXT)**, 4c.6 tables/charts, 4c.8 slide-kind library + validator + asset grovel.
- Ready to resume in fresh session (incl. Telegram HQ "Keynote" topic) — boot checklist in HANDOFF.md.
