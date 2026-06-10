"""
src/kpa/tst_cells.py
=====================

TST cell codec for TableModelArchive baseDataStore.tiles.

Discovered by reverse-engineering ``recon/test1.key`` and ``recon/svef.key``
TST.Tile.rowInfos[*].cellStorageBuffer payloads against the corresponding
TST.TableDataList stringTables.

Format (storageVersion = 5, post-BNC):

Each row in a tile carries:
  - cellCount (u32)              : number of valid cell offsets
  - cellOffsets (base64 bytes)   : array of uint16 LE; 0xFFFF = empty cell
  - cellStorageBuffer (base64)   : concatenated cell records

Cell record (variable length):
  - byte 0   : version tag, always 0x05 in V5
  - byte 1   : format type
                 0x03 = STRING (32-byte record)
                 0x02 = INT64  (44-byte record)
                 0x0a = CURRENCY / large-int (44-byte record)
                 (other formats: formula, rich-text, date — passed through
                  via the escape hatch for now)
  - bytes 2-7  : zero padding
  - bytes 8-11 : flag bitmap (style/format hints)
  - bytes 12-* : payload, depending on format

Payload by format:
  STRING (0x03):     bytes 12-15 = string key (u32 LE) into stringTable
                     bytes 16-31 = style/text-style refs (untouched on edit)
  INT64  (0x02):     bytes 12-19 = value (u64 LE)
                     bytes 20-31 = style refs (untouched on edit)
  CURRENCY (0x0a):   bytes 12-19 = value (u64 LE)
                     bytes 20-31 = style refs + format ref (untouched on edit)

Two convenience APIs:

  - ``decode_row(row_info, strings)`` returns ``list[Cell | None]``
  - ``set_cell_string(row_info, col, value, strings)`` rewrites a single cell
  - ``set_cell_int(row_info, col, value)`` rewrites an INT cell in place
  - ``set_cell_currency(row_info, col, value)`` rewrites a CURRENCY cell

Mutations preserve the cell record's existing style/format refs (the trailing
bytes after the payload), so visual styling survives.

Caveats / limitations:
  - We do NOT decode formula cells, date cells, percentage cells, or
    rich-text cells. Those fall through to the escape hatch.
  - String mutation appends new entries to the stringTable rather than
    reusing existing keys with matching content — keeps the rewrite local
    and reversible. ``compact_string_table`` is a future nice-to-have.
  - Cell length is preserved on edit. Type changes (e.g. INT -> STRING)
    require a record-size change that would shift downstream offsets;
    we raise ``ValueError`` rather than corrupt the buffer. Same-type
    edits work freely.
"""

from __future__ import annotations

import base64
import struct
from dataclasses import dataclass
from typing import Optional, Union


# Format type tags
FMT_EMPTY = 0x00
FMT_INT = 0x02
FMT_STRING = 0x03
FMT_CURRENCY = 0x0a

# Cell record sizes observed in storageVersion=5. These are not
# universal — we've seen 24-byte string cells in some decks (test1.key)
# and 32-byte string cells in others (svef.key). The mutator preserves
# whatever length the existing cell already has.
SIZE_STRING_DEFAULT = 32
SIZE_INT_DEFAULT = 44
SIZE_CURRENCY_DEFAULT = 44
# Back-compat aliases (older code paths).
SIZE_STRING = SIZE_STRING_DEFAULT
SIZE_INT = SIZE_INT_DEFAULT
SIZE_CURRENCY = SIZE_CURRENCY_DEFAULT

# Minimum payload offset for each format (the string key / int value
# starts at byte 12 in every observed cell record).
VALUE_OFFSET = 12

# Sentinel for "no cell at this column"
EMPTY_OFFSET = 0xFFFF


@dataclass
class Cell:
    """A decoded TST cell. ``kind`` is one of 'string'|'int'|'currency'|'raw'.
    For ``kind == 'raw'`` the payload is the unmodified bytes (e.g. for
    formula, date, percentage cells we don't decode yet). The raw bytes
    keep round-trip integrity even when we can't surface a typed value.
    """
    kind: str
    value: Union[str, int, float, bytes, None]
    # The full original cell-record bytes (preserved for round-trip).
    _raw: bytes


def _b64d(s: str) -> bytes:
    if not s:
        return b""
    return base64.b64decode(s)


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _read_offsets(offsets_b: bytes, count: int) -> list[int]:
    """Parse the cell offsets array.

    The base64-decoded bytes are uint16 LE, padded with 0xFFFF terminators
    up to a fixed size (256 entries — tileSize). We only need the first
    ``count`` real offsets.
    """
    if count == 0:
        return []
    n = min(count, len(offsets_b) // 2)
    return list(struct.unpack(f"<{n}H", offsets_b[: n * 2]))


def decode_row(
    row_info: dict, strings: dict[int, str]
) -> list[Optional[Cell]]:
    """Decode a single row's cells.

    Returns a list of length ``cellCount``. Each entry is a Cell, or None
    if the cell is structurally empty (offset = 0xFFFF or absent).
    """
    buf = _b64d(row_info.get("cellStorageBuffer", "") or "")
    offsets_b = _b64d(row_info.get("cellOffsets", "") or "")
    count = int(row_info.get("cellCount", 0) or 0)
    if count == 0 or not buf:
        return []
    offsets = _read_offsets(offsets_b, count)
    # The cell boundary is determined by the next offset; the last cell
    # runs to the end of the buffer.
    boundaries = offsets + [len(buf)]
    out: list[Optional[Cell]] = []
    for i, start in enumerate(offsets):
        if start == EMPTY_OFFSET:
            out.append(None)
            continue
        end = boundaries[i + 1] if (i + 1) < len(boundaries) else len(buf)
        # Skip past any 0xFFFF terminators that may appear in the offset
        # list before the real end-of-buffer.
        if end == EMPTY_OFFSET:
            end = len(buf)
        cell_bytes = buf[start:end]
        out.append(_decode_cell(cell_bytes, strings))
    return out


def _decode_cell(cell: bytes, strings: dict[int, str]) -> Optional[Cell]:
    if len(cell) < 2:
        return Cell(kind="raw", value=cell, _raw=cell)
    fmt = cell[1]
    if fmt == FMT_EMPTY:
        # Style-only cell (no value). Common in empty header slots.
        return Cell(kind="empty", value=None, _raw=cell)
    if fmt == FMT_STRING:
        if len(cell) >= 16:
            sk = struct.unpack("<I", cell[12:16])[0]
            return Cell(kind="string", value=strings.get(sk, ""), _raw=cell)
    elif fmt == FMT_INT:
        if len(cell) >= 20:
            v = struct.unpack("<Q", cell[12:20])[0]
            return Cell(kind="int", value=v, _raw=cell)
    elif fmt == FMT_CURRENCY:
        if len(cell) >= 20:
            v = struct.unpack("<Q", cell[12:20])[0]
            return Cell(kind="currency", value=v, _raw=cell)
    return Cell(kind="raw", value=cell, _raw=cell)


def _next_string_key(strings_archive: dict) -> int:
    next_id = int(strings_archive.get("nextListID", 1))
    return next_id


def _intern_string(strings_archive: dict, value: str) -> int:
    """Ensure ``value`` is in the string table; return its key.

    Reuses an existing entry with the same string (bumps its refcount).
    Otherwise appends a new entry at ``nextListID`` and bumps that
    counter.
    """
    entries = strings_archive.setdefault("entries", [])
    for e in entries:
        if e.get("string") == value:
            e["refcount"] = int(e.get("refcount", 0)) + 1
            return int(e["key"])
    new_key = _next_string_key(strings_archive)
    entries.append({"key": new_key, "refcount": 1, "string": value})
    strings_archive["nextListID"] = new_key + 1
    return new_key


def _release_string_key(strings_archive: dict, key: int) -> None:
    """Decrement refcount; don't delete entries (keep keys stable)."""
    for e in strings_archive.get("entries", []):
        if int(e.get("key", -1)) == key:
            e["refcount"] = max(0, int(e.get("refcount", 1)) - 1)
            return


def _write_row(row_info: dict, cells: list[bytes]) -> None:
    """Rewrite a row's buffer + offsets from a list of cell records.

    Empty cells are encoded with offset 0xFFFF.
    """
    buf = bytearray()
    offsets: list[int] = []
    for c in cells:
        if c is None or len(c) == 0:
            offsets.append(EMPTY_OFFSET)
            continue
        offsets.append(len(buf))
        buf.extend(c)
    # Pad offsets array to the original total length (preserve the 0xFFFF
    # tail used by the canonical encoder).
    orig_offsets_b = _b64d(row_info.get("cellOffsets", "") or "")
    pad_count = max(len(orig_offsets_b) // 2 - len(offsets), 0)
    full = list(offsets) + [EMPTY_OFFSET] * pad_count
    packed = struct.pack(f"<{len(full)}H", *full)
    row_info["cellOffsets"] = _b64e(packed)
    row_info["cellStorageBuffer"] = _b64e(bytes(buf))
    row_info["cellCount"] = len(offsets)


def _row_cells_as_records(row_info: dict) -> list[Optional[bytes]]:
    buf = _b64d(row_info.get("cellStorageBuffer", "") or "")
    offsets_b = _b64d(row_info.get("cellOffsets", "") or "")
    count = int(row_info.get("cellCount", 0) or 0)
    if count == 0 or not buf:
        return []
    offsets = _read_offsets(offsets_b, count)
    boundaries = offsets + [len(buf)]
    out: list[Optional[bytes]] = []
    for i, start in enumerate(offsets):
        if start == EMPTY_OFFSET:
            out.append(None)
            continue
        end = boundaries[i + 1] if (i + 1) < len(boundaries) else len(buf)
        if end == EMPTY_OFFSET:
            end = len(buf)
        out.append(buf[start:end])
    return out


def set_cell_string(
    row_info: dict, col: int, value: str, strings_archive: dict
) -> None:
    """Replace the cell at column ``col`` with a STRING cell carrying
    ``value``. Preserves the existing cell record's style/format refs
    (we keep the byte length unchanged so downstream offsets stay
    correct).

    Raises ValueError if the existing cell is not STRING-typed.
    """
    records = _row_cells_as_records(row_info)
    if col >= len(records):
        raise IndexError(f"col {col} out of range (row has {len(records)} cells)")
    old = records[col]
    if old is None or len(old) < VALUE_OFFSET + 4:
        raise ValueError("cell too short to be a STRING cell")
    if old[1] != FMT_STRING:
        raise ValueError(
            f"cell is not STRING-typed (format=0x{old[1]:02x}); cannot rewrite as string"
        )
    # Release old key, intern new value
    old_key = struct.unpack("<I", old[VALUE_OFFSET:VALUE_OFFSET + 4])[0]
    _release_string_key(strings_archive, old_key)
    new_key = _intern_string(strings_archive, value)
    new = bytearray(old)
    new[VALUE_OFFSET:VALUE_OFFSET + 4] = struct.pack("<I", new_key)
    records[col] = bytes(new)
    _write_row(row_info, records)


def set_cell_int(row_info: dict, col: int, value: int) -> None:
    """Replace the cell at column ``col`` with a new INT value.
    Preserves the cell record's existing byte length; the value is
    written at the canonical offset (bytes 12-19, u64 LE)."""
    records = _row_cells_as_records(row_info)
    if col >= len(records):
        raise IndexError(f"col {col} out of range")
    old = records[col]
    if old is None or len(old) < VALUE_OFFSET + 8 or old[1] != FMT_INT:
        raise ValueError(
            f"set_cell_int requires an existing INT-typed cell (have format="
            f"0x{old[1] if old else 0xff:02x}, len={len(old) if old else 0})"
        )
    new = bytearray(old)
    new[VALUE_OFFSET:VALUE_OFFSET + 8] = struct.pack("<Q", int(value))
    records[col] = bytes(new)
    _write_row(row_info, records)


def set_cell_currency(row_info: dict, col: int, value: int) -> None:
    """Replace the cell at column ``col`` with a new currency value
    (stored as u64). Preserves the cell record's existing byte length.
    Raises if the cell is not CURRENCY-typed."""
    records = _row_cells_as_records(row_info)
    if col >= len(records):
        raise IndexError(f"col {col} out of range")
    old = records[col]
    if old is None or len(old) < VALUE_OFFSET + 8 or old[1] != FMT_CURRENCY:
        raise ValueError(
            f"set_cell_currency requires an existing CURRENCY-typed cell "
            f"(have format=0x{old[1] if old else 0xff:02x}, len="
            f"{len(old) if old else 0})"
        )
    new = bytearray(old)
    new[VALUE_OFFSET:VALUE_OFFSET + 8] = struct.pack("<Q", int(value))
    records[col] = bytes(new)
    _write_row(row_info, records)
