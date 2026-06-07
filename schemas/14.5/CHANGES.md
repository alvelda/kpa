# Keynote 14.5 schema dump

**Source:** `/Applications/Keynote.app/Contents/MacOS/Keynote` (Keynote 14.5,
universal binary, harvested on Intel x86_64, macOS 26.5.1)

**Date:** 2026-06-06

**Method:** `protodump.py` (psobot/keynote-parser, lineage: O'Brien 2013)

## File counts

- 33 `.proto` files recovered.
- Filename convention normalized to `_sos` (underscored), matching the
  keynote-parser 14.4 convention.

## Diff vs Keynote 14.4 (keynote-parser bundled)

**33 / 33 files byte-identical.**

Apple shipped no protobuf schema changes between Keynote 14.4 and 14.5.

The only superficial differences in the raw dump were filename style
(`KNArchives.sos.proto` in 14.5's dumper output vs. `KNArchives_sos.proto`
in the keynote-parser-archived 14.4 set) and matching import paths. After
normalizing the raw dump (script: `scripts/normalize_schema_filenames.sh`),
all 33 files match the 14.4 set byte-for-byte.

## Implication

For the KPA project this means:

1. **R3 (schema drift) is very small for point releases.** Re-harvesting on
   every Keynote update is cheap and we should expect most updates to
   produce zero or minor diffs.
2. We can use **the 14.4 schema set as our working schema** for both
   Keynote 14.4 and 14.5 targets.
3. Schema harvest pipeline is **proven end-to-end** on this corpus.

## What to do for Keynote 15.x

When Apple ships Keynote 15:

```bash
mkdir -p schemas/15.0/raw
.venv/bin/python vendor/keynote-parser/dumper/protodump.py \
    /Applications/Keynote.app schemas/15.0/raw
bash scripts/normalize_schema_filenames.sh schemas/15.0/raw schemas/15.0/normalized
# Diff against 14.5 normalized; write CHANGES.md for 15.0; commit
```

## File list

```
KNArchives.proto                KNArchives_sos.proto
KNCommandArchives.proto         KNCommandArchives_sos.proto
TSAArchives.proto               TSAArchives_sos.proto
TSACommandArchives_sos.proto
TSCEArchives.proto
TSCH3DArchives.proto
TSCHArchives.proto              TSCHArchives_sos.proto
TSCHArchives_Common.proto       TSCHArchives_GEN.proto
TSCHCommandArchives.proto       TSCHPreUFFArchives.proto
TSCKArchives.proto              TSCKArchives_sos.proto
TSDArchives.proto               TSDArchives_sos.proto
TSDCommandArchives.proto
TSKArchives.proto
TSPArchiveMessages.proto        TSPDatabaseMessages.proto
TSPMessages.proto
TSSArchives.proto               TSSArchives_sos.proto
TSTArchives.proto               TSTArchives_sos.proto
TSTCommandArchives.proto        TSTStylePropertyArchiving.proto
TSWPArchives.proto              TSWPArchives_sos.proto
TSWPCommandArchives.proto
```
