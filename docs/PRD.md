# PRD — KPA (Keynote Programmatic Authoring)

**Version:** 1.2
**Author:** Scotty (Chief Engineer, iMac)
**Captain:** Phillip Alvelda
**Created:** 2026-06-06
**Approved:** 2026-06-06 by Captain (Telegram), v1.1 amendment 2026-06-07 07:33 PDT, v1.2 amendment 2026-06-07 08:01 PDT
**License:** MIT (open-source, eventual public release)
**Status:** APPROVED — Step 4a foundation GREEN (commit 213bfd2); Step 4b mutation API next

## Changelog

- **v1.2 — 2026-06-07 08:01 PDT** — **Phase 2 sequence reversed.**
  Per Captain: "Let's move the cross format bridge to before our
  custom live editing canvas work." Phase 2a = Option 5 (PPTX bridge,
  4–6 weeks, PyPI `v0.2`). Phase 2b = Option 4 (custom HTML canvas,
  3–6 months, PyPI `v0.3`). Rationale: ship cross-format value first
  (Claude Design → PPTX → KPA → `.key` becomes usable today), build the
  proprietary canvas as IP moat after, informed by real usage from
  Phase 2a. Option 1 (Claude Design MCP) still queue-jumps any time
  the Anthropic-watch cron fires; complementary to Option 5, not
  redundant.
- **v1.1 — 2026-06-07 07:33 PDT** — Add **surgical editing** as a
  first-class capability (success criterion F2b), alongside end-to-end
  generation. Add **brand-asset grovel** (success criterion F4b) for
  harvesting an asset library from a directory of reference decks.
  Add explicit **coordinate-semantics contract** (pct / pt / px).
  Phase-1 release strategy: 0.1 private to fleet after F1–F5, 0.2
  public after F6–F8. Graphical-review strategy: see
  `docs/GRAPHICAL_REVIEW_OPTIONS.md`.
- **v1.0 — 2026-06-06** — Original PRD.

---

## 0. North Star (Captain's framing, 2026-06-06)

> A complete native-Keynote toolkit that gives Scotty, HAL, **Claude Desktop,
> Claude Code, Claude API agents, and any LLM tool runner in our legion** the
> same level of fluency with `.key` files that the broader ecosystem has with
> `.pptx` and `.pdf` today. Read. Write. Author from scratch. Customize
> existing decks. Apply design systems. Tune layout. Optimize visual quality.
> End to end. No human hand-off.

Everything in this PRD serves that North Star.

## 1. Mission

Build KPA — an open-source Python toolkit, MCP server, OpenClaw skill, and
CLI — that lets any LLM agent in our fleet read, author, design, edit, and
optimize Apple Keynote presentations programmatically with full fidelity to
native Keynote behavior.

Phase 2 extends this to PowerPoint (`.pptx`) and PDF as first-class export
targets; Phase 3 adds full lossless round-trip across all three formats.

## 2. Why Now

- We routinely produce strategy reports (Brainworks/McKinsey style) and
  AI-generated decks. Today every deck requires manual assembly in Keynote
  or fallback to HTML/PDF.
- We already have rich `.pptx` and `.pdf` tooling in the ecosystem (
  python-pptx, pdf libraries, MCP servers). **`.key` is the gap.**
- Direct, agent-grade `.key` authoring closes the loop and lets HAL deliver
  decks the Captain can present from his iPad with zero manual touch.
- Apple has no public file-format spec. We reverse-engineer it ourselves.

## 3. Background & Prior Art

Modern Keynote (`.key`, since 2013) is a **ZIP bundle** containing:
- `Index/*.iwa` — **IWork Archive** files (Snappy-framed, custom-header,
  protobuf-serialized object graphs).
- `Data/*` — embedded images, video, audio.
- `Metadata/`, `preview*.jpg`, `index.apxl.gz` (legacy), thumbnails.

**Existing tools (foundation):**
- `keynote-parser` (psobot, Python) — read/repack `.key`, schemas pinned to
  Keynote 12.x. Mature, MIT-licensed. **Best starting substrate.**
- `keynote-archives` (Lotes, TypeScript) — read-focused browser inspector.
- Andrew Sampson's "Reverse Engineering iWork" (Oct 2025 substack series) —
  current write-up of record structure.

**Critical finding (recon, 2026-06-06):** Keynote 14.5's full protobuf schema
surface is recoverable directly from the application binary at
`/Applications/Keynote.app/Contents/MacOS/Keynote`. Detected `.proto`
files include `KNArchives.proto`, `TSPMessages.proto`, `TSKArchives.proto`,
`TSWPArchives.proto`, `TSCHArchives.proto`, `TSDArchives.proto`,
`TSTArchives.proto`, `TSAArchives.proto`, `TSSArchives.proto`,
`TSCKArchives.proto`, plus their `.sos` and command-archive companions.
**We are not locked to keynote-parser's schema cadence** — we re-harvest on
every Keynote release.

## 4. Scope

### 4.1 In Scope — Phase 1 (Native Keynote Author + Multi-Agent Surface)

**A. Core engine**

1. **Schema harvester** — extract and version the 14.5 protobuf schemas
   from the Keynote binary; compile to Python bindings; diff against
   previous-version schemas to surface breaking changes.
2. **IWA codec** — read/write the IWork Archive container format
   (Snappy framing, varint-length records, archive headers). Fork
   `keynote-parser` as the substrate, extend to 14.5 schemas.
3. **Object-graph authoring layer** — Python module that emits a valid
   `.key` from a high-level Python model. **Native editable** objects
   throughout (no image-of-text or image-of-chart fallbacks):
   - Title slides, section dividers, text+image slides, multi-column layouts.
   - Native text bodies with font/size/color/alignment (uses TSWP).
   - Native shapes and frames (uses TSD).
   - **Native editable chart objects** (uses TSCH) — at minimum: bar,
     column, line, pie, scatter. Each chart is editable in Keynote.app
     and shows the underlying data on double-click.
   - Native image embeds (PNG/JPEG/TIFF) via `Data/`.

**B. Public API (the deliverable)**

Stable Python API consumed by *all* downstream surfaces:
```python
import kpa

deck = kpa.open("/path/to/existing.key")          # read
deck = kpa.Deck(theme=kpa.themes.brainworks_v1)   # new deck
slide = deck.add_slide("title_image")
slide.title = "SIM01: Microbiome Recovery"
slide.add_image("hero.png", layout="right_half")
deck.save("/path/to/out.key")
```
- `kpa.open()`, `kpa.Deck`, `kpa.Slide`, `kpa.Text`, `kpa.Image`,
  `kpa.Chart`, `kpa.Shape`, `kpa.Theme`, `kpa.DesignSpec`.
- All operations are reversible / idempotent / inspectable.
- All objects expose semantic intent (`slide.kind`, `text.role`) not
  just raw protobuf fields.

**C. MCP server**

Wraps the Python API as MCP tools so **Claude Desktop, Claude Code, and any
MCP-aware agent** get KPA as native capabilities:
- `kpa_read_deck(path) -> structured summary + per-slide thumbnails`
- `kpa_inspect_slide(path, slide_idx) -> structured slide content`
- `kpa_edit_slide(path, slide_idx, mutations) -> path`
- `kpa_author_deck(spec, theme) -> path`
- `kpa_apply_theme(path, theme) -> path`
- `kpa_render_thumbnail(path, slide_idx) -> png`
- `kpa_validate(path) -> warnings/errors`
- `kpa_critique(path) -> list of design issues`

The MCP server is the **primary surface** by which non-OpenClaw Claudes
consume KPA. This is what makes the North Star real.

**D. OpenClaw skill**

`brainworks-deck` skill so Scotty/HAL get KPA via the skill-discovery
mechanism (no MCP plumbing required inside OpenClaw).

**E. CLI**

Thin wrapper over the Python API for humans and shell automation:
```
kpa author --spec deck.py --theme brainworks --out deck.key
kpa unpack deck.key out_dir/
kpa pack out_dir/ deck.key
kpa validate deck.key
kpa harvest-schemas /Applications/Keynote.app --out schemas/14.5/
kpa thumbnail deck.key --slide 3 --out s3.png
kpa critique deck.key
```

**F. Design-language layer (first-class, not a polish)**

- `Theme` — colors, fonts, masters, layout grids, spacing rules.
- `DesignSpec` — semantic intent ("section divider," "data slide,"
  "quote slide") that maps to theme primitives.
- Themes harvestable from reference `.key` files: Brainworks SVEF, NCI-FLASH,
  Apple built-ins.
- Themes describable in `design.md` (Captain to supply) and round-trip
  consistent: `harvest_theme(deck) → design.md → apply_theme(new_deck) → matches`.

**G. Critic / optimizer loop**

KPA exposes the *mechanism* for LLM-in-the-loop deck improvement:
- Render slide → thumbnail (via Keynote.app headless or pure-Python renderer
  for v1 fallback).
- LLM critic API (`kpa_critique`) returns structured issues:
  - Text overflow / clipping
  - Title-too-long
  - Color contrast < WCAG AA
  - Off-grid alignment
  - Chart axis labels unreadable
  - (Aesthetic) "imbalanced composition" — LLM-graded against design.md
- Programmatic fixes applied via the same API; re-rendered; re-critiqued.

**H. Round-trip validator**

Open generated decks in Keynote.app via AppleScript / `open -W`, verify no
recovery dialog, save, diff to confirm no semantic drift.

### 4.2 Out of Scope — Phase 1

- `.pptx` and PDF I/O (Phase 2).
- Animations, transitions, build orders (Phase 3 or later).
- Custom-font embedding beyond what Keynote ships.
- Inline video/audio *authoring* (we preserve what reference decks contain;
  Phase 1 does not synthesize new media slides from scratch).
- Pages and Numbers support (different document schemas, same IWA substrate;
  potential future cousin projects).
- Fully sandboxed in-browser renderer (Phase 3+).

### 4.3 Phase 2 (PowerPoint + PDF I/O — separate PRD)

- `.pptx` export from the KPA object model (native OOXML — preserves
  editability in PowerPoint).
- PDF export via Keynote.app's own export (highest fidelity) and via
  headless rendering (no GUI dependency).
- `.pptx` import → KPA object model → re-emit `.key`.
- PDF import remains research-tier and likely Phase 3+.

### 4.4 Phase 3 (full round-trip)

- PDF → editable Keynote.
- Lossless `.key ↔ .pptx ↔ pdf` round-trip with explicit fidelity contracts.

## 5. Success Criteria

### 5.1 Phase 1 — Functional

- [ ] **F1 — Reproduction:** Unpack and repack the SVEF deck and the
      NCI-FLASH deck losslessly. Opens in Keynote 14.5 with no recovery
      dialog and semantically identical on second save.
- [ ] **F2 — Greenfield author:** Generate a 10-slide deck from a Python
      spec using one of (Brainworks, NCI, Apple "Modern Portfolio") as the
      master theme. Open in Keynote, save, no warnings. Must include:
      title slide, section divider, three text+image slides, two
      bullet-list slides, one **native editable chart** slide,
      one quote slide, one closing slide.
- [ ] **F2b — Surgical edit** (added v1.1): Load an existing `.key`
      (SVEF or NCI). Apply five named edits via the API:
      (a) move title block by `dy="20%"`,
      (b) change all body text to Helvetica,
      (c) swap hero image on a specified slide,
      (d) resize an element to `w="40%"`,
      (e) delete a slide.
      Save, re-open in Keynote.app. Every edit persisted; zero
      recovery dialogs; second-save round-trips clean.
- [ ] **F2c — Generation-from-intent** (added v1.1): An agent
      (Scotty/HAL/Claude Desktop) takes a natural-language prompt
      ("Brainworks pitch deck on Project Breathe, 12 slides, video hero
      on slide 5, standard intro") and produces a brand-compliant
      `.key` end-to-end. The agent calls KPA's API for slide construction;
      image/video generation is the agent's responsibility (KPA accepts
      paths and embeds bytes). The output passes F2 and brand-compliance
      checks.
- [ ] **F3 — Chart fidelity:** A KPA-authored chart (bar + line on the
      same axis) opens in Keynote, is editable (data table editable in
      Keynote's chart inspector), and renders identically to the same chart
      authored manually in Keynote.app (visual diff threshold ≤ 1%).
- [ ] **F4 — Brainworks-grade deliverable:** Regenerate a meaningfully
      complex slice of the SVEF deck (≥ 5 slides) from a Python spec,
      theming against the SVEF master. Captain reviews; passes "looks like
      Brainworks made it" sniff test.
- [ ] **F4b — Brand-asset library harvest** (added v1.1): `kpa harvest
      --assets ~/reference-decks/ --out ~/brand-library/` recursively
      scans a directory of `.key` decks and extracts every embedded image
      / video / font / chart-template as a brand-asset library entry,
      deduplicated by content hash, indexed by source deck + slide. The
      library is consumable by `kpa.Deck.use_brand_assets(library)` and
      surfaces to the agent as `deck.brand_assets.search("logo")`.
- [ ] **F5 — Skill integration:** HAL can author a 5-slide brief from a
      natural-language prompt by invoking the `brainworks-deck` skill.

### 5.2 Phase 1 — Multi-agent fluency (North-Star milestone)

- [ ] **F6 — Multi-agent author:** **Claude Desktop**, **Claude Code**, and
      **HAL** each independently produce a 5-slide brief from the **same
      prompt + theme spec** by calling KPA via their respective surface
      (MCP, MCP, skill). A separate Claude grades all three outputs against
      the design.md spec without knowing which agent made which deck. All
      three pass `kpa_validate`; at least two of three pass the design grade.
- [ ] **F7 — Read + critique fluency:** **Claude Desktop** opens an
      existing `.key` (SVEF or NCI), produces a structured summary of each
      slide, identifies three concrete design issues via `kpa_critique`,
      applies fixes via `kpa_edit_slide`, and re-saves. The fixed deck
      passes the validator and the critic re-rates it improved.
- [ ] **F8 — Theme round-trip:** Harvest the Brainworks theme from SVEF
      into `design.md` form; author a fresh deck applying it; visual diff
      against a hand-authored Brainworks deck shows brand-consistent
      colors / fonts / spacing.

### 5.3 Engineering quality

- All Phase 1 schemas re-harvestable from Keynote 14.5 (and Keynote 15.x
  when it ships) by running one command.
- Test suite covers: IWA round-trip, every chart type, every supported slide
  layout, master inheritance, text styling, image embedding, theme apply.
- CI runs the round-trip test against SVEF + NCI on every commit.
- Public API is documented (Sphinx); MCP server is documented at the tool
  level; skill includes worked examples.

## 6. Anti-Goals (explicit non-goals)

- **Not** a Keynote clone or in-browser renderer (Phase 1).
- **Not** a generic protobuf reverse-engineering tool. Scope is `.key`.
- **Not** locked to a single Keynote version. The harvester is the contract.
- **Not** dependent on Keynote.app running for *authoring* (only for testing
  and high-fidelity thumbnail rendering).
- **Not** a closed library. KPA is open-source from day one (MIT).

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **R1 — Object-graph invariants** Keynote rejects (recovery dialog) any deck whose archive IDs, forward refs, or master refs aren't perfectly consistent. | High | High | Build the authoring layer on a known-good template (e.g. SVEF unpacked) and mutate, before attempting greenfield. F1 (round-trip) ships before F2 (greenfield). |
| **R2 — Chart object complexity** TSCH archives are deep nested protobuf trees with hundreds of fields. | High | High | Bootstrap by copying a chart object from a reference deck and mutating its data/labels. Pure greenfield chart authoring is a later sub-phase. |
| **R3 — Schema drift** Apple changes field numbers and adds messages between Keynote versions. | Medium | Medium | Harvester re-runs on every Keynote update. Schemas are versioned in-repo. CI catches breakage. |
| **R4 — IWA framing details** Custom Snappy variant, non-standard varint headers, archive-info wrapper around each protobuf payload. | Medium | Medium | Vendored fork of `keynote-parser` already implements this; we extend, not rewrite. |
| **R5 — macOS sandboxing / iCloud Drive** Generated decks may need extended attributes to open cleanly outside `/tmp`. | Low | Low | Validate by opening from canonical locations (`~/Documents`, iCloud sync folder, AirDrop). |
| **R6 — Apple Silicon port** Schemas and IWA codec are platform-independent; only test harness (AppleScript-driven Keynote validation) differs slightly. | Low | Low | Prototype on iMac (x86_64). Port harness to Studio (arm64) before Phase 2. |
| **R7 — Thumbnail rendering** Needed for the critic loop; depends on Keynote.app (high fidelity) or a pure-Python fallback (lower fidelity). | Medium | Medium | v1 uses Keynote.app for thumbnails on macOS hosts; pure-Python fallback added in F7 with explicit fidelity warning. |
| **R8 — "Beautiful" is unmeasurable** Mechanical issues are testable; aesthetic quality is not. | Medium | Medium | Phase 1 ships mechanical-beauty checks as binary pass/fail and aesthetic-beauty as LLM-graded continuous score. The critic loop is the mechanism; tuning is ongoing. |
| **R9 — Dropbox file-provider deadlocks** (Encountered during recon) | Low | Low | Reference decks are local-cached under `recon/` and `reference-decks/`. |

## 8. Architecture (high level)

```
+-------------------------------------------------------------+
| Consumers (parallel surfaces)                              |
|                                                             |
|  Claude Desktop  Claude Code  Claude API agents             |
|     |               |               |                       |
|     v               v               v                       |
|  +--------------------------------------+                   |
|  |  MCP server (kpa-mcp)                |                   |
|  +--------------------------------------+                   |
|                                                             |
|  Scotty / HAL  ----- OpenClaw skill (brainworks-deck)       |
|                                                             |
|  Humans / scripts ----- CLI (kpa ...)                       |
+-------------------------------------------------------------+
                  |
                  v
+-------------------------------------------------------------+
|  Public Python API (the deliverable)                       |
|    kpa.open / Deck / Slide / Text / Image / Chart / Theme   |
+-------------------------------------------------------------+
                  |
                  v
+-------------------------------------------------------------+
|  Authoring + Critic Layer                                  |
|    - Object-graph builder + ArchiveID allocator             |
|    - ThemeBinding (master slide injection)                  |
|    - DesignSpec → layout primitives                         |
|    - kpa_critique + kpa_render_thumbnail                    |
|    - Mechanical checks (overflow / contrast / grid)         |
|    - Aesthetic checks (LLM-graded against design.md)        |
+-------------------------------------------------------------+
                  |
                  v
+-------------------------------------------------------------+
|  Protobuf Serializer (generated bindings, per Keynote ver.) |
+-------------------------------------------------------------+
                  |
                  v
+-------------------------------------------------------------+
|  IWA Codec (Snappy + framing) + ZIP packer (.key bundle)    |
+-------------------------------------------------------------+
                  |
                  v
+-------------------------------------------------------------+
|  Round-Trip Validator + Thumbnail Renderer                  |
|    - Open in Keynote.app via AppleScript                    |
|    - Capture warnings; save; diff                           |
|    - Render PNG thumbnails per slide                        |
+-------------------------------------------------------------+
        ^
        |
+-------------------------------------------------------------+
|  Schema Harvester (one-time per Keynote release)            |
|    - dumps .proto from Keynote.app                          |
|    - compiles to Python bindings                            |
|    - diffs against previous version                         |
+-------------------------------------------------------------+
```

## 9. Reference Materials

Reference decks (local, recon-confirmed 2026-06-06):
- `recon/svef.key` (55 MB, 186 IWA records, 628 files) — Brainworks SVEF 5-16-26 r2
- `recon/nci.key` (179 MB, 100 IWA records, 325 files) — NCI-FLASH Conference 6-1-26

Public references:
- psobot/keynote-parser (GitHub)
- Lotes/keynote-archives (GitHub)
- Andrew Sampson, "Reverse Engineering iWork" (Oct 2025)
- Archive Team Just Solve the File Format Problem — Keynote
- `/Applications/Keynote.app/Contents/MacOS/Keynote` (binary, schema source of truth)

Brand / template (Captain to supply, per Section 11.1):
- `design.md` (Brainworks)
- `design.md` (NCI)

## 10. Fleet & Runtime

- **Phase 1 dev machine:** iMac (Scotty, Intel x86_64, macOS 26.5.1,
  Keynote 14.5).
- **Phase 1 secondary:** HAL (Mac Studio, Apple Silicon, Keynote 14.5).
- **MCP consumers:** Claude Desktop, Claude Code on Captain's machines.
- Apple-Silicon port: planned at end of Phase 1, before Phase 2 begins.
- KPA is published as an OpenClaw skill (`brainworks-deck`) and as a
  pip-installable package (`kpa`); the MCP server runs locally on each
  Claude-host machine.

## 11. Confirmed Decisions (2026-06-06)

| # | Decision | Status |
|---|----------|--------|
| 11.1 | **Name:** KPA (Keynote Programmatic Authoring) | ✅ confirmed |
| 11.2 | **License:** MIT (open-source) | ✅ confirmed |
| 11.3 | **design.md** (Brainworks + NCI) supplied by Captain when ready; blocks F2/F4/F8 only | ✅ confirmed |
| 11.4 | **Phase split:** Phase 1 = `.key`; Phase 2 = `.pptx` + PDF export; Phase 3 = full round-trip | ✅ confirmed |
| 11.5 | **Output fidelity:** Native editable Keynote objects throughout. No image-fallback for charts. | ✅ confirmed |
| 11.6 | **Reference decks:** Brainworks SVEF + NCI-FLASH | ✅ confirmed (located on disk) |
| 11.7 | **Spec format:** Python DSL primary, plus Keynote-native format where useful (intermediate representation) | ✅ confirmed |
| 11.8 | **Target Keynote version:** Latest (14.5 on Captain's fleet today) | ✅ confirmed |
| 11.9 | **Dev fleet:** Prototype on iMac (Intel); port to HAL (Apple Silicon) at end of Phase 1 | ✅ confirmed |
| 11.10 | **North Star:** Read/write/author/customize/optimize fluency for Scotty + HAL + Claude Desktop + Claude Code + any Claude/agent | ✅ confirmed |

## 12. Sign-off

Once Captain approves PRD v0.2:
1. Promote to PRD v1.0 (drop DRAFT marker).
2. Write `docs/DEV_PLAN.md` with phased checkbox list.
3. **Sync-commit GATE** — `git init`, push planning artifacts to GitHub and
   mirror to HAL **before any execution work begins**.
4. WorkManager entry created.
5. Phase 1 execution starts.

— Scotty
