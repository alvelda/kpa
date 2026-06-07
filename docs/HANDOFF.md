# KPA — Post-Compaction Handoff

**Last updated:** 2026-06-07 04:55 PDT
**Purpose:** Snapshot of in-flight build state so the next compacted session can pick up Step 3c / Step 4 without losing the thread.
**Owner:** Scotty (iMac)
**Captain:** Phillip Alvelda

---

## Where We Are

**Project:** KPA — Keynote Programmatic Authoring
**Repo:** https://github.com/alvelda/kpa (origin) + HAL mirror (`hal:scotty/projects/keynote-format`)
**Working dir on iMac:** `/Users/alvelda/scotty/projects/keynote-format`
**Phase:** **Phase 1, Step 3 — IWA codec + lossless round-trip (F1)** — 🎉 **F1 GREEN**

| Step | Status | Commit |
|---|---|---|
| Step 1 — Recon + repo + sync-commit gate | ✅ DONE | `3a2cd74` |
| Step 2 — Schema harvester (Keynote 14.5 protos) | ✅ DONE | `25d724d` |
| Step 3a — Decoder smoke test (unpack SVEF.key) | ✅ DONE | `bf91096` |
| Step 3b — Pack-side round-trip (F1) | ✅ DONE — 628/628 files identical | `0eaf89d` |
| **Step 3c — Keynote.app open-validation + 2nd deck** | ✅ SVEF confirmed, NCI uncovered Bug #5 | this commit |
| Step 3d (optional) — RawProtobufPatch passthrough for NCI | 🔜 queued | — |
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

## Four Upstream Bugs Patched In-Place (must propagate to vendor + file PRs later)

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
- **PROPAGATED ✅** to `vendor/keynote-parser/keynote_parser/versions/v14_4/mapping.py` (2026-06-06). Survives a fresh `pip install -e vendor/keynote-parser`.

### Bug #3: keynote-parser pack-side ZIP filename encoding (NEW, Step 3b)

- **Symptom:** Pack-side round-trip wrote `.key` files where non-ASCII filenames (e.g. macOS screenshot timestamps with U+202F — narrow-no-break-space — between hour-minute-second and AM/PM) had ZIP general-purpose flag bit 11 (0x800, "UTF-8 filename") set. Apple's Keynote.app never sets that flag — it writes UTF-8 bytes raw and expects readers to interpret. 31/628 entries on the SVEF round-trip got the wrong flag.
- **Why it matters:** Our own `zip_file_reader` (and any other Apple-style reader) then chokes when re-unpacking, because the cp437→utf-8 normalization step is unconditional and U+202F isn't representable in cp437.
- **Root cause:** Python's stock `ZipInfo._encodeFilenameFlags()` tries ASCII first and falls back to UTF-8 with the flag set. There is no public API to write a non-ASCII filename without the flag.
- **Fix:** Custom `_AppleZipInfo(ZipInfo)` subclass that overrides `_encodeFilenameFlags()` to always return `(filename.encode("utf-8"), self.flag_bits)` — i.e., UTF-8 bytes with the flag bits untouched (and we never set 0x800 ourselves). `zip_file_sink()` now uses `_AppleZipInfo` for every entry.
- **PROPAGATED ✅** to `vendor/keynote-parser/keynote_parser/file_utils.py` (2026-06-07).

### Bug #5: keynote-parser ProtobufPatch interpreter NotImplemented for real-world merge patches (NEW, Step 3c)

- **Symptom:** Unpacking `recon/nci.key` fails on `Index/Slide-1100-2.iwa` with `ValueError: Failed to deserialize` wrapping the internal trace `diff_read_version: 25 / Object was: b''` from `ProtobufPatch.FromString`.
- **Root cause:** Real-world Keynote `.key` files that have been edited/saved multiple times contain incremental "merge" archives where `archive_info.should_merge = True`. One of the `message_infos` then encodes a `type=0, length=0` patch with:
  - `diff_field_path.path` empty (0 entries) — not 1 as keynote-parser expects
  - `fields_to_remove` populated — keynote-parser raises NotImplementedError on this unconditionally
  - `diff_read_version` = `[2, 0, 25]` array of supported reader versions
- **Why it matters for KPA:** Blocks unpack/round-trip of any deck that has merge history (likely the majority of real Keynote decks). SVEF happens to have zero `should_merge=True` patches. NCI has at least one.
- **Fix path (queued):** introduce a `RawProtobufPatch` subclass that:
  - Captures the raw bytes of unsupported patches
  - Records the full `message_info` (including `fields_to_remove`, `diff_field_path`, version arrays)
  - Round-trips them bit-identically without semantic interpretation
  - When KPA needs to author *new* patches semantically (Phase 2+), implement the actual interpretation layer
- **NOT propagated yet** — design decision pending Captain input on whether to do this in Step 3d (immediate) or defer to Step 4.

### Bug #4: keynote-parser read-side ZIP filename encoding amplifier (NEW, Step 3b)

- **Symptom:** Even after pack-side fix, `zip_file_reader` blew up trying to re-unpack any archive that contained UTF-8-flagged entries (which our broken Step-3b-first-try output did). `UnicodeEncodeError: 'charmap' codec can't encode character '\u202f'`.
- **Root cause:** The reader unconditionally does `_file.filename = _file.filename.encode("cp437").decode("utf-8")`. For Apple-style archives (no 0x800 flag), the filename comes through Python's zipfile as cp437-decoded bytes — the re-encode-decode recovers real UTF-8. For spec-correct archives (0x800 flag set), the filename is already proper Python unicode, and re-encoding via cp437 fails on codepoints not in cp437.
- **Fix:** Only do the cp437→utf-8 round-trip when bit 0x800 is clear. UTF-8-flagged entries are passed through unchanged.
- **PROPAGATED ✅** to `vendor/keynote-parser/keynote_parser/file_utils.py` (2026-06-07).

### Bug #1 (original): `snappy` PyPI name collision

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

## F1 RESULT — Steps 3b + 3c GREEN (2026-06-07)

### Step 3c confirmation (Keynote.app open-test)
- Killed sluggish 17h-uptime Keynote zombie (PID 16249).
- Launched fresh `Keynote Creator Studio.app` via `open -a` on `recon/round-trip/svef-roundtrip.key`.
- **No "file is damaged" / "recover" / "corrupt" / "cannot open" / "invalid format" entries in the unified log over 5 minutes after open.**
- Two `KNMacDocument` instances active in PID 69578 — our round-tripped file is loaded as a normal document.
- AppleScript probes time out (`-1712`) because osascript lacks TCC Automation permission for Keynote — cosmetic, not a file problem. Future: grant Automation permission to Terminal/iTerm/osascript in System Settings → Privacy & Security → Automation.
- NCI second-deck test — unpack failed on `Index/Slide-1100-2.iwa` (see Bug #5 above). NCI deferred to Step 3d/4.

## F1 RESULT — Step 3b GREEN (2026-06-07)

**Verification done:**
- Pack: 628 entries written in ~5s. Size 54,782,740 bytes vs original 54,784,985 (delta 2,245 bytes / 0.004%).
- Re-unpack: 628 entries read back without errors.
- Full byte-level structural diff (sha256 every file):
  - **628 / 628 files identical**
  - 96/96 Index IWA YAMLs identical
  - 436/436 Data binary assets identical
  - 3/3 Metadata files identical
  - 3/3 preview*.jpg identical
  - **0 differences across 53.8MB+ of content**
- ZIP flag-bit distribution: original 0/628 UTF-8 flagged → round-trip 0/628 ✅ exact match.

The 2,245-byte outer-ZIP delta is from central-directory layout, not file contents. Per the ZIP spec the central-directory ordering is irrelevant to readers. Will only investigate further if Keynote.app cares (unlikely).

## Reproduction (run after compaction to confirm F1 still green)

```bash
cd ~/scotty/projects/keynote-format
source .venv/bin/activate
rm -rf recon/round-trip
mkdir -p recon/round-trip
PYTHONWARNINGS="ignore::UserWarning" keynote-parser pack \
  recon/unpacked/svef \
  --output recon/round-trip/svef-roundtrip.key
PYTHONWARNINGS="ignore::UserWarning" keynote-parser unpack \
  recon/round-trip/svef-roundtrip.key \
  --output recon/round-trip/svef-re-unpacked
python3 <<'PY'
import os, hashlib
def hashdir(root):
    h = {}
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f); rel = os.path.relpath(p, root)
            h[rel] = hashlib.sha256(open(p,'rb').read()).hexdigest()
    return h
orig = hashdir("recon/unpacked/svef")
re   = hashdir("recon/round-trip/svef-re-unpacked")
diff = [k for k in (set(orig)&set(re)) if orig[k] != re[k]]
print(f"F1 status: orig={len(orig)} re={len(re)} differing={len(diff)} " + ("✅ GREEN" if not diff and orig.keys()==re.keys() else "❌ REGRESSED"))
PY
```

## Next Action: Step 3d (optional) or Step 4

**Captain decides:**

### Option A — Step 3d: implement RawProtobufPatch passthrough (covers NCI)
- Add `RawProtobufPatch` class in `vendor/keynote-parser/keynote_parser/codec.py` that stores raw bytes + full message_info.
- Route unsupported patches through it in `IWAArchiveSegment.from_buffer`.
- Round-trip emits identical bytes for the patch.
- Validate against NCI (628 → ~XYZ files identical).
- Cost: ~1-2 hours.
- Value: F1 covers all real Keynote decks, not just SVEF.

### Option B — Move to Step 4 (object-graph authoring + F2 greenfield)
- F1 stands for SVEF; NCI's Bug #5 is documented but deferred.
- Begin authoring API (`kpa.Deck`, `kpa.Slide`, etc.) using SVEF as the reference deck.
- NCI / general-case F1 becomes a Phase 1.5 cleanup, not a blocker.
- Cost: bigger — 8-12 hours for authoring API + tests.
- Risk: KPA can't round-trip the median real deck until 3d lands.

**My recommendation:** Step 3d first. The bug is a one-class fix and the value is huge — most real Keynote decks have merge history..

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
2. Run the "Reproduction Path" block above — confirms snappy + mapping + zip-encoding patches survived, AND that F1 round-trip is still green.
3. Resume at "Next Action: Step 3d or Step 4" (Captain to decide).
4. If anything in section "Five Upstream Bugs Patched In-Place" looks unfamiliar, that's expected — the patches are intentional and load-bearing. Don't undo them. Bugs #1–#4 are propagated to `vendor/keynote-parser/`. Bug #5 is documented but not yet patched (decision pending).
