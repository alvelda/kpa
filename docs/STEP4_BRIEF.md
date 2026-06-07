# Step 4 Planning Brief — Object-Graph Authoring + Python API (F2)

**Author:** Scotty
**Date:** 2026-06-07
**Status:** DRAFT — awaiting Captain's answers to blocker questions before
                 PRD/DEV_PLAN tightening and code work begins.

> Per HAL Dev Workflow: brief → questions → PRD/DEV_PLAN tightening →
> sync-commit gate → execution. Step 4 corresponds to PRD §4.1.A.3 and
> success criterion F2 (greenfield author). It is the gateway from
> "we can preserve real Keynote files" (F1 ✅) to "we can author native
> Keynote files from a Python spec" (F2).

---

## Mission

Build the Python authoring layer that lets an agent (Scotty, HAL, Claude
Desktop, Claude Code) construct a `.key` file from a high-level Python
specification, opening cleanly in Keynote 14.5 with no recovery dialog.

This is the **first checkpoint where KPA produces value beyond what
psobot/keynote-parser already provided.** F1 was about losslessness;
F2 is about authoring.

### Captain's clarifying directive (2026-06-07 07:33 PDT)

Two capability modes are equally first-class deliverables of Step 4 + 5:

1. **End-to-end generation from intent** — Scotty or HAL receives a prompt
   like "design a Brainworks pitch deck on Project Breathe with 12 slides,
   the standard intro, and a video hero on slide 5" and KPA produces a
   brand-compliant native `.key` end-to-end (text + images + video + chart
   placeholders + master/theme bindings).

2. **Surgical editing of existing decks** — "move the title block down
   20% and change the font to Helvetica," "swap the chart on slide 7 to a
   stacked bar," "replace the hero image on slide 3 with this new file."
   Edits must be deterministic, addressable, and idempotent across re-saves.

Both modes share the same object model and the same brand-compliance
validator. Neither mode is a stretch goal; both are S4-class success
criteria.

## Scope

### In Scope (Step 4)

1. **Core object model** — `kpa.Deck`, `kpa.Slide`, `kpa.TextBlock`,
   `kpa.Image`, `kpa.Shape`, `kpa.MasterRef` — Python classes that map to
   the IWA archive graph.
2. **Archive-ID allocator** — collision-free, deterministic ID assignment
   across the deck. Forward-reference safe.
3. **Template-anchored authoring** — `kpa.Deck.from_template(svef_or_nci)`
   loads an existing deck as the substrate; new slides inherit its masters,
   themes, fonts, colors automatically. This is R1 mitigation (PRD §7) —
   we mutate a known-good graph rather than build greenfield from zero.
4. **Slide-kind taxonomy (growing)** — start by inventorying every distinct
   slide kind already present in SVEF and NCI. Each becomes a `kpa.SlideKind`
   entry. New kinds added by harvesting future reference decks; agents and
   humans both author against the same growing library.
5. **Surgical-edit address book** (NEW, per Captain 2026-06-07 07:33 PDT) —
   every authored or imported object exposes a **stable addressable handle**:
   - `slide[3].title`, `slide[3].body`, `slide[3].image[0]`
   - or semantic: `slide.where(role="title")`, `slide.where(kind="title")`
   - all `kpa.Element` objects expose `.move(dx, dy)`, `.resize(w, h)`,
     `.set_position(x, y, units="pct|pt|px")`, `.set_font(name, size?)`
   - addresses survive re-save round-trips (deterministic on object IDs).
6. **Brand-compliance validator** (NEW, per Captain's clarification) —
   every mutation runs against the active `kpa.Theme`:
   - non-theme fonts rejected (or warned, configurable)
   - non-palette colors flagged
   - off-grid coordinates auto-snapped (or flagged)
   - master-overriding edits explicitly opt-in via `brand_override=True`
7. **Media slots** — native image and video embed (PNG/JPEG/TIFF/MP4/MOV)
   via `Data/` + Asset Manager. The full "generate this image from a prompt"
   integration with `image_generate`/`video_generate` is wired but the
   generation call itself is the *caller's* responsibility — KPA accepts a
   path, embeds the bytes, anchors the archive ref.
8. **CLI:** `kpa author --spec deck.py --template svef.key --out deck.key`
   (template flag optional; defaults to a bundled brand-neutral template).
   Plus surgical sub-commands: `kpa edit deck.key 'slide[3].title.move(dy="20%")'`
   shell-friendly mutation expressions.
9. **Validators:** every mutation goes through an invariant checker
   (every `ArchiveRef` resolves to a real archive; every required field
   populated; protobuf round-trips clean).
10. **F2 test gate:** the 10-slide deck described in PRD §5.1 F2 opens
    in Keynote 14.5 with no recovery dialog and saves clean on second open.
11. **F2-edit test gate** (NEW) — take SVEF, apply five surgical edits
    via the API (move element, change font, swap image, resize image,
    delete a slide), re-save, re-open in Keynote.app, verify each edit
    persisted and the deck is recovery-dialog-free.
12. **CI extension:** add `tests/test_authoring.py` and `tests/test_edits.py`
    that produce F2 deck + F2-edit deck headlessly and run `kpa validate`.

### Out of Scope (Step 4 — handled by later steps)

- Charts (Step 5, success criterion F3)
- Theme harvesting + DesignSpec (Step 6, success criterion F8) — brand-
  compliance validator in Step 4 consumes the theme passively; the harvest
  pipeline that produces themes from reference decks ships in Step 6.
- MCP server / skill / critic (Step 7)
- Multi-column or complex compound layouts (deferred to Step 5/6)
- Animations, transitions, builds (Phase 3+)
- Generative media calls themselves (Step 4 accepts a file path; the
  `image_generate` / `video_generate` call lives at the agent layer, not
  inside KPA core)
- Pure-greenfield (no template) authoring — Phase 1.5 stretch goal
- Master-slide editing (we *use* masters; we don't *author* them in Step 4)

## Success Criteria (Step 4)

- [ ] **S4.1** — `kpa.Deck.from_template("recon/svef.key")` round-trips
       byte-identical (no-op mutation = F1 still passes).
- [ ] **S4.2** — Authored 10-slide deck (PRD F2 spec) opens in Keynote 14.5
       with zero recovery / warning dialogs.
- [ ] **S4.3** — Same 10-slide deck saves cleanly on second open.
- [ ] **S4.4** — Re-opening Scotty-authored deck via `kpa.open(...)` reads
       back the same logical structure (slide count, kinds, text content).
- [ ] **S4.5** — Archive-ID allocator runs against SVEF + NCI without
       collisions; pruning detects orphan archives.
- [ ] **S4.6** — Public API surface is documented (docstrings +
       `docs/authoring.md`).
- [ ] **S4.7** — CI runs S4.2 + S4.4 + S4.9 on every commit on `main`.
- [ ] **S4.8** — Slide-kind taxonomy populated from SVEF + NCI inventory
       (one entry per unique kind detected) before greenfield authoring
       begins.
- [ ] **S4.9** — **Surgical-edit suite:** load SVEF, apply five named
       edits via the API —
       (a) move title block by `dy="20%"`,
       (b) change all body text to Helvetica,
       (c) swap hero image on slide 3,
       (d) resize an element to `w="40%"`,
       (e) delete a slide —
       save, re-open in Keynote.app, verify every edit persisted, zero
       recovery dialogs.
- [ ] **S4.10** — **Brand-compliance validator:** authored decks pass the
       active theme's font/color/grid checks; intentional overrides
       require `brand_override=True` and emit a warning to the audit log.

## Approach

**Template-anchored, not greenfield.** Real Keynote object graphs have
hundreds of cross-referencing archives — masters, themes, layouts,
style-cascades, color palettes — and Keynote rejects any deck whose
forward references aren't perfectly consistent (R1).

Greenfield authoring requires synthesizing all of that *first*, which
is a tall hill before we have ground-truth signal. **We instead bootstrap
by:**

1. Loading a known-good template deck (SVEF or NCI) into the KPA object
   model.
2. Identifying the "slide insertion points" — where slide archives are
   created, registered in the slide tree, linked to the navigator,
   added to the thumbnail index.
3. Cloning a master-derived slide of the desired kind, mutating it
   (text content, image refs, position adjustments), and re-anchoring it.
4. Pruning original template slides we don't want.

This means **the first deliverable F2 deck looks like SVEF with new
content**. That's intentional: it proves the authoring pipeline works
end-to-end before we tackle pure-greenfield.

Pure greenfield (no template) is queued as a Phase 1.5 stretch goal
after F2 + F3 (charts) are green.

### Coordinate semantics (NEW, per Captain's clarification)

All positional edits accept three unit systems:

- `"pct"` — percentage of the slide canvas (default for human-style edits).
  `move(dy="20%")` moves the element down 20% of the slide height.
- `"pt"` — points, native Keynote unit, used internally by IWA archives.
  `move(dy=144)` moves 144 points (2 inches at 72 DPI).
- `"px"` — pixels at the canvas's native resolution (mostly for video / image
  sizing). Auto-converted to points based on `slide.canvas_size`.

The reference frame for `move(dx, dy)` is the element's current position;
`set_position(x, y)` uses the slide canvas origin (top-left, like macOS
screen coordinates). All three units round-trip clean through Keynote.app.

### Surgical-edit DSL

For the CLI / shell form:

```
kpa edit deck.key 'slide[3].title.move(dy="20%")'
kpa edit deck.key 'slides.where(role="title").body.set_font("Helvetica")'
kpa edit deck.key 'slide[7].chart[0].swap_data("new.csv")'
```

Under the hood these are parsed into the same Python API calls; the
CLI is sugar.

### Generation-from-intent pipeline (orchestrated outside KPA core)

The "design a Brainworks deck on Project Breathe with 12 slides and a
video hero on slide 5" workflow is a *composition* on top of KPA:

```python
# Inside an agent (Scotty/HAL/Claude Desktop):
from kpa import Deck, themes
deck = Deck.from_template(themes.brainworks_v1)         # KPA
for slide_spec in plan_deck_with_llm(prompt, n=12):    # agent
    if slide_spec.needs_hero_image:
        img = await image_generate(slide_spec.image_prompt)  # tool
        slide_spec.assets["hero"] = img.path
    if slide_spec.needs_video:
        vid = await video_generate(slide_spec.video_prompt)  # tool
        slide_spec.assets["hero_video"] = vid.path
    deck.add_slide_from_spec(slide_spec)                # KPA
deck.brand_compliance.assert_clean()                    # KPA
deck.save("breathe-pitch.key")                          # KPA
```

KPA's role: object model + slide construction + brand validation + IWA
emit. The LLM planning, image/video generation, and orchestration are
the *caller's* job and live in skills / MCP layer (Step 7) or in HAL's
research agent. This keeps KPA core deterministic and testable.

## Open Questions (BLOCKING — need Captain's input)

These genuinely block PRD/DEV_PLAN tightening. None are stylistic.

### Q1 — Default template

When the user calls `kpa.Deck()` without specifying a template, what
does KPA use as the base?

- **Option A:** SVEF (Brainworks-themed). All Scotty-authored decks look
  like Brainworks decks unless overridden. Fits "make Brainworks-grade
  decks easy."
- **Option B:** NCI-FLASH. Cleaner / lighter / less brand-specific.
- **Option C:** Apple's stock "Modern Portfolio" or "White" theme.
  Most-neutral starting point; ships independent of our reference decks.
- **Option D:** No default — `kpa.Deck()` requires an explicit template
  arg. Forces the agent to be deliberate.

**Scotty's recommendation:** **C (Apple "White" or "Modern Portfolio")**
shipped as a vendored minimal template. Reasoning: keeps KPA brand-neutral
for the open-source release, doesn't ship anyone else's IP, easy default
for new agents, Brainworks/NCI themes still available via explicit
`from_template=` arg.

### Q2 — Authoring spec format (Python DSL shape)

The PRD (§4.1.B) shows one shape:
```python
deck = kpa.Deck(theme=kpa.themes.brainworks_v1)
slide = deck.add_slide("title_image")
slide.title = "..."
slide.add_image("hero.png", layout="right_half")
```

Three competing shapes worth considering:

- **A — Imperative builder (PRD shape above)** — verbose, explicit, easy
  to debug, reads like a recipe. Best for agents writing one slide at a
  time.
- **B — Declarative dict / JSON** — `kpa.Deck.from_spec({"slides": [...]})`.
  Best for LLMs emitting deck-specs as structured output. Aligns with MCP
  tool-call shape.
- **C — Both** — imperative builder is canonical; dict/JSON is sugar.

**Scotty's recommendation: C** — imperative is the truth, declarative is a
shim. MCP server (Step 7) will need the declarative path anyway since
tool-call payloads are JSON, so we may as well design both together.

### Q3 — Slide-kind taxonomy

PRD F2 lists six slide kinds. Are those names locked, and which exact set?

**Proposed canonical set (six kinds, lowercase snake_case):**

- `title` — large centered title, optional subtitle/byline
- `section_divider` — color-fill, single section name, optional roman numeral
- `text_image` — title + body text + image (variants: left, right, full-bleed)
- `bullet_list` — title + bullet body (1–6 bullets)
- `quote` — large quoted text + attribution
- `closing` — "Thank you" / contact card / Q&A

**Open variants per kind:** does `text_image` need to be three kinds
(`text_image_left`, `text_image_right`, `text_image_full`) or one kind
with a `layout=` arg?

**Scotty's recommendation:** Six kinds, layout variants as args. Easier
to grow later; agents only need to remember six names.

### Q4 — Where do the F2 test images live?

The 10-slide F2 deck (PRD §5.1) needs hero images. Today there is no
"KPA reference image set."

- **Option A:** Pull a handful of public-domain / CC0 images into
  `recon/test-assets/` (sized to typical slide proportions).
- **Option B:** Use Brainworks marketing images from SVEF as the test
  set (already vendored).
- **Option C:** Generate placeholder images at test-time (solid color +
  caption) so we have no asset dependency.

**Scotty's recommendation:** A + C. Ship a small CC0 set (3–4 images,
~5MB) so F2 produces a credible-looking deck humans can read, but make
the test-suite version use C so CI doesn't depend on the assets being on
disk.

### Q5 — Round-trip-with-mutation gate

Today CI runs F1 (unpack/repack/re-unpack) against SVEF + NCI. Step 4
introduces a new class of validation:

> Author a deck. Open it. Save it. Re-open the saved version. Verify
> structural equivalence.

This requires either:

- **Option A — AppleScript-driven Keynote.app** — most authoritative but
  brittle, slow, GUI-dependent, requires TCC Automation permission
  (currently blocked on this iMac per Step 3c findings).
- **Option B — Headless re-validation through KPA itself** — `kpa.open(
  path) → kpa.save(path2) → unpack(path1) == unpack(path2)`. Cheap, fast,
  CI-friendly, but doesn't catch Keynote.app-specific recovery dialogs.
- **Option C — Both** — B in CI on every commit; A as a manual `make
  validate-app` step run before release.

**Scotty's recommendation: C.** B is the daily safety net; A is the
release gate.

### Q6 — Phase 2 trigger criterion

The PRD says Phase 2 (`.pptx` + PDF) starts after Phase 1 ships. Phase 1
has eight steps. **Do we ship Phase 1 as a 0.x release once F1-F5 are
green**, or do we hold the public release until F6-F8 (multi-agent
fluency + theme round-trip) also pass?

**Scotty's recommendation:** Ship `0.1` once F1-F5 are green (private to
the fleet); ship `0.2` once F6-F8 also pass (public open-source
announcement). This gives us a working tool for HAL and the legion months
before public launch.

## Risks (Step 4-specific)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **S4-R1: Slide-tree invariants** Keynote rejects mutated decks whose `slidelist`, `nav`, and thumbnail indexes drift out of sync with the actual slide archives. | High | High | Build a `SlideTreeManager` that enforces all four updates atomically. Test on every mutation. |
| **S4-R2: Master-slide implicit refs** Slides inherit dozens of style fields from masters via cascading refs. Mutating a slide's master breaks the cascade. | High | Med | Step 4 disallows master mutation; we only consume masters. Step 6 unlocks master authoring. |
| **S4-R3: Text-layout protobuf is huge** TSWP archives have hundreds of fields per text block (kerning, ligatures, listStyle, etc.). | Med | Med | Clone a known-good text block from the template and only override the literal `text` field + the style-id ref. |
| **S4-R4: Image asset re-anchoring** New images need entries in `Data/`, a stable name (`<name>-<id>.<ext>`), a `Datas` archive entry, and a fill/imageMedia ref. | Med | Med | Ship an `AssetManager` that handles all four atomically. Property-based test against SVEF's existing images. |
| **S4-R5: ID-allocator drift** If we allocate new archive IDs that collide with existing template IDs, Keynote either silently overwrites or rejects. | High | High | ID allocator reads the template's `max_id` first, allocates above it, and verifies non-collision before write. |
| **S4-R6: F2 deck looks like SVEF** Template-anchored authoring means the first F2 deliverable visually resembles its template, which may surprise Captain who wants "neutral" output. | Med | Low | Q1 above selects the default template. If neutral is wanted, ship a stripped Apple-template default. |
| **S4-R7: Step 4 estimate underruns** Object-graph authoring is the single hardest part of Phase 1. Days 5-8 in the original plan may be optimistic. | High | Med | Break Step 4 into 4a/4b/4c/4d sub-steps with explicit gates. Adjust schedule transparently. |

## Estimate

- **Optimistic:** 3 working days (24 focused hours)
- **Realistic:** 5 working days (40 focused hours)
- **Pessimistic:** 8 working days (64 focused hours)

Recommended sub-step breakdown:

- **4a** — `SlideTreeManager` + ID allocator + `kpa.Deck.from_template`
        round-trip parity gate (1-2 days).
- **4b** — `kpa.TextBlock` mutation, `kpa.Slide` add/remove, three
        slide kinds (title, text_image, bullet_list) green (1-2 days).
- **4c** — Remaining three slide kinds (section_divider, quote, closing) +
        `kpa.Image` AssetManager (1 day).
- **4d** — F2 test green + CI integration + `docs/authoring.md`
        (1 day).

Each sub-step is its own commit + push (per HAL Dev Workflow).

## Dependencies / Blockers

None new. Phase 1 read-side is complete (Steps 1-3 ✅). Step 4 is
unblocked for execution as soon as Q1-Q6 are answered.

## Out of this brief, by design

- Step 5 (charts) gets its own brief when 4 ships. TSCH archives are deep
  enough to warrant their own focused planning round.
- Step 6 (themes), Step 7 (MCP/critic), and Step 8 (release) are all
  sequenced after Step 5 lands.

---

## Next moves (waiting on Captain)

1. Captain answers Q1-Q6 (probably 10 minutes of decisions).
2. Scotty tightens DEV_PLAN Step 4 into 4a/4b/4c/4d with the answers folded in.
3. Sync-commit gate (planning artifacts pushed to GitHub + HAL).
4. Step 4a code starts.

— Scotty
