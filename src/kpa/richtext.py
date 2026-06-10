"""
src/kpa/richtext.py
====================

TSWP rich-text decode/encode for :class:`TSWP.StorageArchive` payloads.

Apple's text storage in Keynote is **range-table based**. A
StorageArchive carries:

  - ``text``: list[str]  (concatenated to give the full text body)
  - ``tableParaStyle``  : paragraph-style overrides keyed by start-index
  - ``tableParaStarts`` : paragraph boundary metadata (one root entry)
  - ``tableParaData``   : per-paragraph data (alignment, indent hooks)
  - ``tableListStyle``  : bullet/list-style overrides
  - ``tableDropCapStyle``: drop-cap overrides
  - ``tableParaBidi``   : RTL/LTR hints
  - ``tableCharStyle``  : *inline* character-style overrides (bold runs,
    font-size changes, links — anything that varies mid-paragraph)

Each "table" is a dict ``{entries: [...]}`` where each entry has shape::

    {"characterIndex": <int>, "object": {"identifier": <style_id>}}

The entries are sorted by ``characterIndex``. The style ref carries
through until the next entry's index. Entries without an ``object``
field clear the previous override.

This module exposes the structure as a flat list of paragraphs
(``Paragraph(text, style_id, list_style_id, runs)``) where each
paragraph has its own char-style runs (``Run(text, style_id)``). That's
the shape agents reason about ("title bold, body normal, second bullet
has one bold word in the middle") without having to track character
offsets by hand.

Public API:

    decode_storage(storage)  -> list[Paragraph]
    encode_storage(storage, paragraphs)  -> None  (in-place rewrite)

Caveats:
  - Paragraphs are split on ``\n`` (LF). The U+2028 line separator
    keeps the same paragraph (it's a soft line break within one
    paragraph, matching Keynote's distinction between Enter and
    Shift+Enter).
  - Encode preserves any style ref the caller passes through. If a
    style ref is left as ``None`` we drop that entry (Keynote falls
    back to the storage's stylesheet master).
  - tableParaStarts is left as a single root entry ``[{characterIndex:0,
    first:0, second:0}]`` (matches every recon deck we've inspected).
  - tableParaBidi entries default to ``{first:65535, second:65535}``
    (LTR neutral) per recon deck convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------- public dataclasses ----------------------


@dataclass
class Run:
    """One inline character-style run inside a paragraph."""
    text: str
    char_style_id: Optional[str] = None


@dataclass
class Paragraph:
    """One paragraph (logical line ended by LF)."""
    text: str
    para_style_id: Optional[str] = None
    list_style_id: Optional[str] = None
    drop_cap_style_id: Optional[str] = None
    para_bidi: Optional[tuple[int, int]] = None
    para_data: Optional[tuple[int, int]] = None
    # When ``runs`` is empty, the whole paragraph uses a single implicit
    # run with no char-style override. When non-empty, the runs'
    # concatenated text must equal ``text``.
    runs: list[Run] = field(default_factory=list)


# ---------------------- helpers ----------------------


def _entries(table: Optional[dict]) -> list[dict]:
    if not isinstance(table, dict):
        return []
    return list(table.get("entries", []) or [])


def _style_id(entry: dict) -> Optional[str]:
    obj = entry.get("object")
    if isinstance(obj, dict):
        v = obj.get("identifier")
        if v is not None:
            return str(v)
    return None


def _style_at(entries: list[dict], char_idx: int) -> Optional[str]:
    """Return the style-id active at ``char_idx`` (longest characterIndex
    <= char_idx)."""
    active: Optional[str] = None
    for e in entries:
        ci = int(e.get("characterIndex", -1))
        if ci <= char_idx:
            active = _style_id(e)
        else:
            break
    return active


def _bidi_at(entries: list[dict], char_idx: int) -> Optional[tuple[int, int]]:
    active: Optional[tuple[int, int]] = None
    for e in entries:
        ci = int(e.get("characterIndex", -1))
        if ci <= char_idx:
            f = int(e.get("first", 65535))
            s = int(e.get("second", 65535))
            active = (f, s)
        else:
            break
    return active


def _data_at(entries: list[dict], char_idx: int) -> Optional[tuple[int, int]]:
    active: Optional[tuple[int, int]] = None
    for e in entries:
        ci = int(e.get("characterIndex", -1))
        if ci <= char_idx:
            f = int(e.get("first", 0))
            s = int(e.get("second", 0))
            active = (f, s)
        else:
            break
    return active


# ---------------------- decode ----------------------


def storage_text(storage: dict) -> str:
    """Return the full text content of a TSWP.StorageArchive as a single string."""
    t = storage.get("text", [])
    if isinstance(t, list):
        return "".join(x for x in t if isinstance(x, str))
    return str(t) if t else ""


def decode_storage(storage: dict) -> list[Paragraph]:
    """Decode a TSWP.StorageArchive into a flat list of :class:`Paragraph`."""
    text = storage_text(storage)
    if not text:
        return []

    para_style_entries = _entries(storage.get("tableParaStyle"))
    list_style_entries = _entries(storage.get("tableListStyle"))
    drop_cap_entries = _entries(storage.get("tableDropCapStyle"))
    bidi_entries = _entries(storage.get("tableParaBidi"))
    data_entries = _entries(storage.get("tableParaData"))
    char_style_entries = _entries(storage.get("tableCharStyle"))

    # Split text on LF into paragraphs. Each paragraph spans
    # [para_start, para_end) in character coordinates. The trailing LF
    # is implicit \u2014 the para's text does NOT include it.
    paragraphs: list[Paragraph] = []
    cursor = 0
    n = len(text)

    # We split on '\n' only (NOT on U+2028 \u2028 line separator \u2014 those
    # are soft breaks inside one paragraph, matching Keynote's
    # Enter-vs-Shift+Enter distinction).
    while cursor <= n:
        # Find next \n (or end).
        nl = text.find("\n", cursor)
        if nl == -1:
            para_end = n
        else:
            para_end = nl
        para_text = text[cursor:para_end]

        para = Paragraph(
            text=para_text,
            para_style_id=_style_at(para_style_entries, cursor),
            list_style_id=_style_at(list_style_entries, cursor),
            drop_cap_style_id=_style_at(drop_cap_entries, cursor),
            para_bidi=_bidi_at(bidi_entries, cursor),
            para_data=_data_at(data_entries, cursor),
            runs=_decode_runs(para_text, cursor, char_style_entries),
        )
        paragraphs.append(para)

        if nl == -1:
            break
        cursor = nl + 1
    # If the text ends with \n we end up with an empty trailing paragraph
    # \u2014 keep it; that's how a final newline is represented.
    if text.endswith("\n"):
        paragraphs.append(
            Paragraph(
                text="",
                para_style_id=_style_at(para_style_entries, n),
                list_style_id=_style_at(list_style_entries, n),
                drop_cap_style_id=_style_at(drop_cap_entries, n),
                para_bidi=_bidi_at(bidi_entries, n),
                para_data=_data_at(data_entries, n),
            )
        )
    return paragraphs


def _decode_runs(
    para_text: str, para_start: int, char_style_entries: list[dict]
) -> list[Run]:
    """Slice ``para_text`` into runs based on the active char-style
    entries in [para_start, para_start+len(para_text)].

    Returns ``[]`` if the paragraph has a single implicit run (no
    char-style varies within the paragraph). Returns a list of
    explicit :class:`Run` instances when there are mid-paragraph
    style changes.
    """
    if not para_text:
        return []
    para_end = para_start + len(para_text)

    # Find every char-style entry whose characterIndex falls inside
    # [para_start, para_end). Plus we need the style active at
    # para_start (whose characterIndex may be <= para_start).
    boundaries: list[int] = [para_start]
    style_at_boundary: dict[int, Optional[str]] = {
        para_start: _style_at(char_style_entries, para_start)
    }
    for e in char_style_entries:
        ci = int(e.get("characterIndex", -1))
        if para_start < ci < para_end:
            boundaries.append(ci)
            style_at_boundary[ci] = _style_id(e)
    boundaries.append(para_end)

    # If there's only one segment and it has no style override, return
    # ``[]`` (implicit single run).
    if len(boundaries) == 2 and style_at_boundary[para_start] is None:
        return []

    runs: list[Run] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        seg = para_text[start - para_start : end - para_start]
        if not seg:
            continue
        runs.append(Run(text=seg, char_style_id=style_at_boundary[start]))
    return runs


# ---------------------- encode ----------------------


def encode_storage(storage: dict, paragraphs: list[Paragraph]) -> None:
    """Rewrite a TSWP.StorageArchive in place from a list of
    :class:`Paragraph` instances.

    Preserves existing top-level fields (``styleSheet``, ``inDocument``,
    etc.) and only rewrites the text body + the seven range tables.
    """
    # 1. Concatenate paragraph text. Paragraphs are joined by '\n'.
    parts: list[str] = []
    para_offsets: list[int] = []  # start index of each paragraph
    cursor = 0
    for i, p in enumerate(paragraphs):
        para_offsets.append(cursor)
        parts.append(p.text)
        cursor += len(p.text)
        # Append '\n' between paragraphs (and after a trailing empty
        # paragraph, but skipping the last non-empty one keeps round-trip
        # parity with Keynote's convention of omitting a final \n).
        if i < len(paragraphs) - 1:
            parts.append("\n")
            cursor += 1
    text = "".join(parts)
    text_len = len(text)

    storage["text"] = [text]

    # 2. tableParaStarts: always one root entry.
    storage["tableParaStarts"] = {
        "entries": [{"characterIndex": 0, "first": 0, "second": 0}]
    }

    # 3. tableParaStyle: one entry per paragraph (omitting style ref is
    #    OK \u2014 Keynote falls back to the storage's master style).
    para_style_entries = []
    for p, off in zip(paragraphs, para_offsets):
        e: dict = {"characterIndex": off}
        if p.para_style_id is not None:
            e["object"] = {"identifier": str(p.para_style_id)}
        para_style_entries.append(e)
    if not para_style_entries:
        para_style_entries = [{"characterIndex": 0}]
    storage["tableParaStyle"] = {"entries": para_style_entries}

    # 4. tableListStyle: one entry per paragraph (carries bullet/list).
    list_entries = []
    for p, off in zip(paragraphs, para_offsets):
        e = {"characterIndex": off}
        if p.list_style_id is not None:
            e["object"] = {"identifier": str(p.list_style_id)}
        list_entries.append(e)
    if not list_entries:
        list_entries = [{"characterIndex": 0}]
    storage["tableListStyle"] = {"entries": list_entries}

    # 5. tableDropCapStyle.
    drop_entries = []
    for p, off in zip(paragraphs, para_offsets):
        e = {"characterIndex": off}
        if p.drop_cap_style_id is not None:
            e["object"] = {"identifier": str(p.drop_cap_style_id)}
        drop_entries.append(e)
    if not drop_entries:
        drop_entries = [{"characterIndex": 0}]
    storage["tableDropCapStyle"] = {"entries": drop_entries}

    # 6. tableParaBidi. Default to 65535/65535 (LTR neutral).
    bidi_entries = []
    for p, off in zip(paragraphs, para_offsets):
        f, s = p.para_bidi if p.para_bidi else (65535, 65535)
        bidi_entries.append({"characterIndex": off, "first": f, "second": s})
    if not bidi_entries:
        bidi_entries = [{"characterIndex": 0, "first": 65535, "second": 65535}]
    storage["tableParaBidi"] = {"entries": bidi_entries}

    # 7. tableParaData. Default to (0, 0).
    data_entries = []
    for p, off in zip(paragraphs, para_offsets):
        f, s = p.para_data if p.para_data else (0, 0)
        data_entries.append({"characterIndex": off, "first": f, "second": s})
    if not data_entries:
        data_entries = [{"characterIndex": 0, "first": 0, "second": 0}]
    storage["tableParaData"] = {"entries": data_entries}

    # 8. tableCharStyle: per-paragraph runs.
    char_entries: list[dict] = []
    for p, off in zip(paragraphs, para_offsets):
        if not p.runs:
            # One implicit run with no override.
            char_entries.append({"characterIndex": off})
            continue
        # Verify runs concat to paragraph text.
        joined = "".join(r.text for r in p.runs)
        if joined != p.text:
            raise ValueError(
                f"paragraph runs don't match paragraph text: "
                f"runs={joined!r} text={p.text!r}"
            )
        run_cursor = off
        for r in p.runs:
            e: dict = {"characterIndex": run_cursor}
            if r.char_style_id is not None:
                e["object"] = {"identifier": str(r.char_style_id)}
            char_entries.append(e)
            run_cursor += len(r.text)
    if not char_entries:
        char_entries = [{"characterIndex": 0}]
    storage["tableCharStyle"] = {"entries": char_entries}

    # Validation: every range-table's final characterIndex must be <=
    # text_len. (Equality is allowed for an end-of-text marker.)
    for k in (
        "tableParaStyle",
        "tableListStyle",
        "tableDropCapStyle",
        "tableParaBidi",
        "tableParaData",
        "tableCharStyle",
    ):
        for e in storage[k]["entries"]:
            ci = int(e.get("characterIndex", 0))
            if ci > text_len:
                raise ValueError(
                    f"{k} entry has characterIndex {ci} > text length {text_len}"
                )
