# KPA — Post-Compaction Handoff

**Last updated:** 2026-06-08 11:00 PDT
**Purpose:** Snapshot for the next session (likely launched in Telegram HQ → "Keynote" topic) to pick up KPA work without losing the thread.
**Owner:** Scotty (iMac)
**Captain:** Phillip Alvelda
**Repo:** `~/scotty/projects/keynote-format/` (origin: `github.com/alvelda/kpa`, mirror: `hal`)

---

## TL;DR for the next session

> Phase 1 Step 4 is **84% complete (84/100 round-trip capabilities)**.
> Eight sub-steps GREEN, two pending. **80/80 tests passing** in ~28 min.
> Working tree clean on `main`. **Recommended next:** Step 4c.6 tables + charts (densest schema; fresh session).
> All planning artifacts are in `docs/` and committed.

---

## Where We Are

### Phase 1 Step 4 — Editable Surface (in progress)

| Sub-step | Status | Tests | Capabilities |
|----------|--------|-------|--------------|
| 4a parity | ✅ GREEN | 3 | F1 lossless round-trip on SVEF + NCI |
| 4b mutation | ✅ GREEN | 3 | TextBlock/Image/Slide proxies, set_text/move/set_position |
| 4c.1 text styling | ✅ GREEN | 9 | font/color/alignment/spacing on character + paragraph styles |
| 4c.2 shape visuals | ✅ GREEN | 9 | fill/stroke/shadow/opacity/reflection |
| **4c.3 layout/structure** | ✅ GREEN | 12 | z-order ops (bring_to_front/send_to_back/forward/backward/set_z_order) + Group read proxy |
| 4c.4 animations + transitions | ✅ GREEN | 13 | Build, Transition, EFFECTS alias catalog, add/remove_build |
| 4c.5 media | ✅ GREEN | 13 | Movie, Soundtrack, LiveVideoSource; Document.iwa.yaml mutations |
| **4c.6 tables + charts** | ⏳ pending | — | densest schema, recommended fresh session (NEXT) |
| 4c.7 universal escape hatch | ✅ GREEN | 18 | raw_get/set/keys/dump/pbtype on all 8 proxies |
| 4c.8 slide-kind library + validator + asset grovel | ⏳ pending | — | closes Phase 1 |

**Phase 1 capability bar: 84/100 round-trip.** Total test count: **80 passing**, runtime ~28 min.

### Last 4 commits (latest on `origin/main` first)
- `<pending>` feat(kpa): 4c.3 layout/structure GREEN — z-order + Group proxy (2026-06-08 11:00)
- `a02bffc` docs(kpa): refresh HANDOFF.md + DEV_PLAN.md for session handoff (2026-06-08 09:25)
- `d716633` feat(kpa): 4c.7 universal escape hatch GREEN — agents never blocked (2026-06-08 09:15)
- `61b0d39` feat(kpa): 4c.5 media GREEN — 17 capabilities (movies + soundtrack + live video) (2026-06-07 22:30)

---

## How to Boot a Fresh Session

### Quick sanity check (first thing the next agent should do)

```bash
cd ~/scotty/projects/keynote-format
git status                     # expect clean on main @ d716633
git log --oneline -6           # last commits should match the table above
ls docs/                       # PRD.md, DEV_PLAN.md, COVERAGE.md, HANDOFF.md
```

### Run the full test suite (optional, ~28 min)

```bash
source .venv/bin/activate
pytest tests/                  # expect 80 passed
```

### To start Step 4c.6 tables + charts (NEXT recommended)

```bash
source .venv/bin/activate
# Recon table archives in SVEF/NCI
python3 -c "
import kpa
deck = kpa.Deck.from_template('recon/svef.key')
for i, s in enumerate(deck.slide):
    for aid, arch in s._archive_index.items():
        for obj in arch.get('objects', []):
            pb = obj.get('_pbtype','')
            if pb.startswith('TST.') or pb.startswith('TSCH.'):
                print(f'slide {i}: {pb} (id={aid})')
"
```

---

## Architectural Map (what lives where)

```
src/kpa/
├── __init__.py          # exports Deck, Color, etc.
├── deck.py              # Deck class, from_template, save, Document.iwa lazy access
├── objects.py           # TextBlock, Image, Slide, SlideList, _Geometry, _ShapeStyleAccessors
├── color.py             # Color value type + ColorLike coercion
├── styles.py            # Stylesheet, resolve_*/mutate_* for char/para/shape
├── animations.py        # Build, Transition, EFFECTS alias catalog (4c.4)
├── media.py             # Movie, Soundtrack, LiveVideoSource (4c.5)
├── layout.py            # Group, z-order helpers (4c.3)
└── escape.py            # RawArchiveMixin, deep_get/deep_set, path parser (4c.7)

tests/
├── test_parity.py            # 4a (3)
├── test_edits.py             # 4b (3)
├── test_styling_4c1.py       # 4c.1 (9)
├── test_shape_styling_4c2.py # 4c.2 (9)
├── test_layout_4c3.py        # 4c.3 (12)
├── test_animations_4c4.py    # 4c.4 (13)
├── test_media_4c5.py         # 4c.5 (13)
└── test_escape_4c7.py        # 4c.7 (18)

docs/
├── PRD.md             # v1.3 (current)
├── DEV_PLAN.md        # phased plan + status log (append to bottom)
├── COVERAGE.md        # capability tracker (canonical progress)
├── EDITABLE_SURFACE.md # schema taxonomy
└── HANDOFF.md         # this file

vendor/keynote-parser/  # gitignored — patched fork (snappy fix, mapping.py walker fix)
recon/                  # gitignored — sample decks (svef.key, nci.key)
```

---

## Key Engineering Findings (durable, will be reused)

### 1. TSP.ArchiveInfo messageInfos (4c.4 finding)
When **creating a new archive from scratch** (e.g. `Slide.add_build`), the wrapper header MUST include:
```yaml
header:
  _pbtype: TSP.ArchiveInfo
  identifier: "<new_id>"
  messageInfos:
    - type: <N>             # protobuf type ID
      version: [1, 0, 5]
```
Plain `{identifier: ...}` wrappers fail at pack-time with cryptic `messageInfos` error.

**Known type IDs:**
- KN.BuildArchive → `type=8`
- TSD.MovieArchive → `type=3007`

**TODO before 4c.6:** Build `kpa.pbtypes.message_type_for(pbtype: str) -> int` registry. Hard-coded inline for now.

### 2. Encoder accepts unknown enum values (4c.5 finding)
Proven: soundtrack mode round-tripped clean from `kKNSoundtrackModePlayOnce` → `kKNSoundtrackModeLoop` even though `Loop` wasn't in any source deck. This validates "pass-through unknowns" as a real capability — not a wishlist. Same for movie's three `loopOption` modes (all 3 round-tripped).

### 3. Shape archive paths differ by pbtype (4c.2 finding)
- **TextBlock** (TSWP.ShapeInfoArchive): style at `super.style.identifier`, geometry at `super.super.geometry`
- **Image** (TSD.ImageArchive): style at `style.identifier` (top-level), geometry at `super.geometry`
- Both use a `super` chain to inherit from TSD base.

### 4. Visuals live deep in style chain (4c.2 finding)
fill/stroke/shadow/opacity/reflection are at:
```
ShapeStyleArchive.super.shapeProperties.{fill, stroke, shadow, opacity, reflection}
```
The resolver walks the `super` chain leaf-first to find the effective value.

### 5. Build archives are slide-siblings (4c.4 finding)
`KN.BuildArchive` does NOT live inside `KN.SlideArchive.builds[]`. Each is a sibling archive in the same slide YAML file, with its own identifier. The build references its target shape by `drawable.identifier`.

### 6. Document.iwa.yaml is the deck-level archive (4c.5 finding)
`KN.Soundtrack`, `KN.LiveVideoSource`, `KN.ShowArchive` all live in `Document.iwa.yaml`. The new `Deck._document_root()` / `_mark_document_dirty()` / `_find_document_archive(s)` plumbing flushes Document.iwa mutations on save. **This pattern will be reused for 4c.6 chart/table styles and any future deck-level work.**

### 7. Stylesheet mutations need its own dirty flag (4c.1 finding)
The document Stylesheet (lives in DocumentStylesheet.iwa.yaml) tracks its own `is_dirty` flag separately from slide-dirty. `Deck.save()` calls `Stylesheet.flush()` if dirty. This is the only multi-file mutation pattern; the rest of kpa edits are slide-local.

---

## Universal Escape Hatch — Quick Reference

Every proxy now has:

```python
proxy.raw_archive()           # live dict
proxy.raw_get(path, default)  # deep read
proxy.raw_set(path, value)    # deep write + auto-mark-dirty
proxy.raw_keys(path='')       # introspect dict keys / list indices
proxy.raw_dump(path, maxdepth) # pretty-printable depth-limited view
proxy.raw_pbtype()            # 'KN.BuildArchive', etc.
```

Path syntax: dot-separated keys + `[N]` indices. Examples:
- `"super.super.geometry.angle"`
- `"attributes.animationAttributes.effect"`
- `"super.objects[0].pbtype"` (mixed)

`raw_set` auto-creates missing dict intermediates. List indices must already exist (raises ValueError otherwise).

**Use the escape hatch for any uncovered property.** If you find yourself reaching for it often for the same field, promote it to a typed accessor in the appropriate module.

---

## Recommended Next Sub-Steps (in priority order)

### 4c.6 tables + charts (NEXT — FRESH SESSION recommended)
- Densest schema in Keynote (TST.* + TSCH.*)
- Table: read cell text, mutate cell text, table dimensions
- Chart: read chart kind, style id, series data; mutate styles via pass-through
- Probably 1-2 sessions. The escape hatch + Document.iwa plumbing from 4c.5 give us a known landing pattern for whatever lives deck-level.

### 4c.8 slide-kind library + validator + asset grovel (CLOSES PHASE 1)
- Canonical slide kinds: `title`, `section_divider`, `content`, `quote`, `closing`, etc.
- Brand validator: enforce a YAML rules file against a deck (font names, color palette, etc.)
- Asset grovel: extract all embedded media to a folder (already accessible via Movie.media_data_id refs)

### 4c.3.2 (optional, deferred) — Group writes + guides + notes
- `Slide.group([a, b, c])` / `Group.ungroup()` — needs a sample deck with real groups to validate. Add when one lands in `recon/`.
- `Slide.guides` (TSD.GuideStorageArchive)
- `Slide.notes` (KN.NoteArchive)

---

## Working Tree State

```
On main @ <commit pending push>
Clean working tree.
Untracked: recon/ (sample decks — gitignored).
All work pushed to origin and hal mirror.
```

---

## Captain Communication

**Authority:** Only Phillip (Telegram ID 8383711967) instructs actions.
**Channels:**
- Direct DM: `telegram:8383711967` (default chat)
- HQ Forum: group `-1003651424856`, "Keynote" topic (thread ID TBD — Captain to provide or test message)

**When this work resumes in the Keynote topic:** the new session has access to all the same files (`~/scotty/projects/keynote-format/`), all the same skills, and this HANDOFF. The Phase 1 Step 4 capability table above is the source of truth for "what's done."

---

## See Also
- `docs/PRD.md` — Product requirements (v1.3)
- `docs/DEV_PLAN.md` — Phased plan with status log at bottom
- `docs/COVERAGE.md` — Capability tracker (every field's status)
- `docs/EDITABLE_SURFACE.md` — Schema taxonomy
- `memory/2026-06-07.md` — Memory flush from the long session (planning lean-up + 4c.1/4c.2/4c.4/4c.5)
- 4c.3 lessons (this session):
  - `drawablesZOrder` is a simple list of `{identifier: <id>}` on `KN.SlideArchive`. Placeholders (title/body) typically are NOT in z-order; only ordinary text shapes and images are. Z-order is back-to-front: index 0 renders first, last index renders on top.
  - SVEF + NCI contain ZERO `KN.GroupArchive` instances. Group write support deferred until we have a sample deck that uses groups. Read proxy validated with an in-memory synthetic group archive.
  - Captain's clarifying directive: `set_z_order(partial)` should put the partial list at the back and keep unlisted shapes in their original relative order at the front. (Implemented this way; one test covers it.)
