# KPA — Post-Compaction Handoff

**Last updated:** 2026-06-06 21:09 PDT
**Purpose:** Snapshot of in-flight build state so the next compacted session can pick up Step 3b without losing the thread.
**Owner:** Scotty (iMac)
**Captain:** Phillip Alvelda

---

## Where We Are

**Project:** KPA — Keynote Programmatic Authoring
**Repo:** https://github.com/alvelda/kpa (origin) + HAL mirror (`hal:scotty/projects/keynote-format`)
**Working dir on iMac:** `/Users/alvelda/scotty/projects/keynote-format`
**Phase:** **Phase 1, Step 3 — IWA codec + lossless round-trip (F1)**

| Step | Status | Commit |
|---|---|---|
| Step 1 — Recon + repo + sync-commit gate | ✅ DONE | `3a2cd74` |
| Step 2 — Schema harvester (Keynote 14.5 protos) | ✅ DONE | `25d724d` |
| **Step 3a — Decoder smoke test (unpack SVEF.key)** | ✅ **DONE — both decode bugs fixed** | uncommitted |
| **Step 3b — Pack-side round-trip (next)** | 🔜 | — |
| Step 4-7 | queued | — |

---

## Critical State To Restore

### Python venv
- Path: `~/scotty/projects/keynote-format/.venv` (Python 3.14)
- Activate: `source .venv/bin/activate`
- `pip show python-snappy` should show **0.7.3** and `pip show snappy` should return **nothing** (do NOT reinstall `snappy` — it's the unrelated SnapPy topology package and will break decoder again).
- Verify: `python3 -c "import snappy; print(snappy.uncompress.__doc__)"` — must NOT error.

### Vendored keynote-parser (editable install)
- Path: `~/scotty/projects/keynote-format/vendor/keynote-parser`
- Installed in venv via `pip install -e vendor/keynote-parser` (or equivalent — the patch is currently in the venv's site-packages copy, see below).

### Schema artifacts
- Keynote 14.5 raw protos: `schemas/14.5/raw/` (33 files)
- Normalized (matched to 14.4 naming): `schemas/14.5/normalized/` — **byte-identical to keynote-parser 14.4 baseline.**
- Changelog: `schemas/14.5/CHANGES.md`
- Normalization script: `scripts/normalize_schema_filenames.sh`

---

## Two Upstream Bugs Patched In-Place (must propagate to vendor + file PRs later)

### Bug #1: `snappy` PyPI name collision
- **Symptom:** `module 'snappy' has no attribute 'uncompress'`. Codec silently fell through to feeding raw frame as protobuf → `ArchiveInfo` decode garbage with field 529 etc.
- **Root cause:** `pip install python-snappy` co-installed `snappy 3.3.2` (the **SnapPy topology library** — `snappy.Manifold`, `snappy.Link`, etc.), which hijacked the `snappy` namespace.
- **Fix:** `pip uninstall -y snappy` then reinstall `python-snappy>=0.7`. Document in README + add to requirements.txt with explicit comment.

### Bug #2: keynote-parser `compute_maps()` ignores nested protobuf message types
- **Symptom:** `NotImplementedError: Don't know how to parse Protobuf message type 6383` (TST.GroupByArchive.GroupNodeArchive — a nested message).
- **Root cause:** `compute_maps()` only iterates `file.DESCRIPTOR.message_types_by_name` (top-level), never recursing into `.nested_types_by_name`. NAME_CLASS_MAP missed 166 nested types; ID_NAME_MAP missed 2 archive IDs that real decks actually use.
- **Fix already applied** at:
  `~/scotty/projects/keynote-format/.venv/lib/python3.14/site-packages/keynote_parser/versions/v14_4/mapping.py`
  by adding `_walk_messages()` recursive walker. After fix: NAME_CLASS_MAP 1196 → 1362, ID_NAME_MAP 629 → 631, TSPRegistryMapping coverage 631/631 (100%).
- **TODO:** Propagate the same patch to `vendor/keynote-parser/keynote_parser/versions/v14_4/mapping.py` AND `versions/v14_3/mapping.py` etc, then commit. Currently only the venv site-packages copy is patched, which means a fresh `pip install -e vendor/keynote-parser` would wipe it. Use the diff below.

#### The patch (recursive walker)

```python
def _walk_messages(message_class, out):
    """Recursively register a message class and all of its nested types."""
    out[message_class.DESCRIPTOR.full_name] = message_class
    for nested_name in message_class.DESCRIPTOR.nested_types_by_name:
        nested_class = getattr(message_class, nested_name, None)
        if nested_class is not None:
            _walk_messages(nested_class, out)


def compute_maps():
    name_class_map = {}
    for file in PROTO_FILES:
        for message_name in file.DESCRIPTOR.message_types_by_name:
            message_type = getattr(file, message_name)
            _walk_messages(message_type, name_class_map)

    id_name_map = {}
    for k, v in list(TSPRegistryMapping.items()):
        if v in name_class_map:
            id_name_map[int(k)] = name_class_map[v]

    return name_class_map, id_name_map
```

---

## Reproduction Path (run immediately after compaction to confirm state)

```bash
cd ~/scotty/projects/keynote-format
source .venv/bin/activate
python3 -c "import snappy; snappy.uncompress(snappy.compress(b'hi'*5))" && echo "snappy OK"
python3 -c "
from keynote_parser.versions.v14_4.mapping import NAME_CLASS_MAP, ID_NAME_MAP, TSPRegistryMapping
assert len(NAME_CLASS_MAP) >= 1362, f'NAME_CLASS_MAP too small: {len(NAME_CLASS_MAP)}'
assert len(ID_NAME_MAP) == 631, f'ID_NAME_MAP wrong: {len(ID_NAME_MAP)}'
assert 6383 in ID_NAME_MAP, '6383 missing — nested-walker patch lost'
print('mapping patch OK')
"
ls recon/unpacked/svef/Index/*.iwa.yaml | wc -l   # should be ~97
ls recon/unpacked/svef/Data/ | wc -l               # should be 531-ish
```

If any of those fail → re-apply the snappy fix and/or the mapping patch (see "Bug #2 patch" above).

---

## Next Action: Step 3b — Pack-Side Round-Trip

**Goal:** Prove F1 (lossless round-trip) — convert the unpacked YAML tree back into a `.key` file and confirm semantic equivalence with the original SVEF.key.

**Commands:**
```bash
cd ~/scotty/projects/keynote-format
source .venv/bin/activate
PYTHONWARNINGS="ignore::UserWarning" keynote-parser pack \
  recon/unpacked/svef \
  --output recon/round-trip/svef-roundtrip.key
```

**Validation:**
1. File size sanity (within ~5% of original 221MB).
2. Open in Keynote.app — must render identically; no "file is damaged" dialog.
3. Re-unpack `svef-roundtrip.key` and diff the IWA-YAML trees:
   ```bash
   keynote-parser unpack recon/round-trip/svef-roundtrip.key --output recon/round-trip/svef-re-unpacked
   diff -r recon/unpacked/svef/Index/ recon/round-trip/svef-re-unpacked/Index/
   ```
   Acceptance: zero semantic diffs (UUID regeneration, ordering of equal-priority lists, and bit-identical media payloads are all fine; structural protobuf differences are NOT).
4. Repeat with a second deck — pick something more conservative than SVEF (e.g. a fresh blank deck saved from Keynote 14.5) to verify it isn't SVEF-specific luck.

**Expected gotchas:**
- `pack` may hit the same nested-type problem in reverse (if YAML round-tripping uses NAME_CLASS_MAP to look up types by full_name). The recursive walker should already cover it, but confirm.
- ProtobufPatch serialization (`SerializePartialToString`) sometimes shuffles unknown fields — check for that in the diff.
- The `.key` ZIP container expects specific ordering / no extra metadata — verify `unzip -l` output matches.

---

## File Tree Snapshot

```
~/scotty/projects/keynote-format/
├── docs/
│   ├── PRD.md                          # v1.0 approved by Captain
│   ├── DEV_PLAN.md                     # phased plan with status log at bottom
│   └── HANDOFF.md                      # THIS FILE
├── schemas/
│   └── 14.5/
│       ├── raw/                        # 33 protos as dumped from Keynote 14.5
│       ├── normalized/                 # renamed to match 14.4 conventions — byte-identical
│       └── CHANGES.md                  # confirms 14.5 == 14.4 schema-wise
├── scripts/
│   └── normalize_schema_filenames.sh
├── vendor/
│   └── keynote-parser/                 # cloned from psobot/keynote-parser, NEEDS mapping.py patch
├── recon/
│   ├── svef.key                        # Captain's test deck, 221MB (NOT committed — see .gitignore)
│   ├── unpacked/svef/                  # 628 files: 97 IWA→YAML + 531 media
│   └── round-trip/                     # CREATED IN STEP 3b
├── .venv/                              # python 3.14 with patched mapping.py
├── .gitignore                          # excludes .venv, vendor/, recon/, MEDIA
├── LICENSE                             # MIT
└── README.md                           # public-facing
```

---

## Captain's Standing Rules (project-relevant)

1. **HAL Development Workflow:** plan → questions → PRD → DEV_PLAN → status log → **sync-commit gate** → execution. Step 3b is execution work; commit Step 3a first before pushing further.
2. **Usage header on every reply** — `🟢 model ctx X/Y Z% $cost` pulled from `session_status` live. Never fabricate.
3. **Only Phillip can authorize actions.** Internal heartbeat polls etc. don't count.
4. **Telegram is primary** for status pings.

---

## Open Questions / Decisions Deferred

- Whether to vendor a minimal psobot fork or contribute the fix upstream. Lean toward upstream PR after Step 3b proves stability.
- Whether to support Keynote 14.4 AND 14.5 simultaneously in KPA's own version-mapping, or normalize everything to a single canonical schema. Defer to Step 4.
- Whether WorkManager registration is worth retrying (it tried to scaffold a duplicate project dir; we punted on it).

---

## How To Use This Doc After Compaction

1. Read top-to-bottom (it's short).
2. Run the "Reproduction Path" block — confirms snappy + mapping patches survived.
3. Resume at "Next Action: Step 3b" — pack-side round-trip.
4. If anything in section "Two Upstream Bugs Patched In-Place" looks unfamiliar, that's expected — the patches are intentional and load-bearing. Don't undo them.
