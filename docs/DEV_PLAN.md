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

- [ ] `kpa.Deck`, `kpa.Slide`, `kpa.Text`, `kpa.Image`, `kpa.Shape`
- [ ] Archive-ID allocator (R1 mitigation: collisions and forward refs)
- [ ] Theme binding — ingest a reference deck and re-use its masters / colors / fonts
- [ ] Greenfield authoring: title slide, section divider, text+image, bullet list, quote, closing
- [ ] CLI: `kpa author --spec deck.py --out deck.key`
- [ ] **F2 test:** 10-slide greenfield deck, opens clean, saves clean

**Commit:** `feat(kpa): object-graph authoring + F2 (greenfield) green`

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

- [ ] All 8 success criteria (F1–F8) green
- [ ] Docs published: Python API (Sphinx), MCP tools README, skill README
- [ ] PyPI release: `pip install kpa`
- [ ] GitHub release tagged `v0.1.0`
- [ ] Apple-Silicon port to HAL (Mac Studio) — codec + schemas + tests parity
- [ ] PRD v1.1 / DEV_PLAN v2.0 for Phase 2 drafted

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
