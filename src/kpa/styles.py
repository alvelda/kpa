"""
kpa.styles — Document stylesheet + style resolution
====================================================

Step 4c.1. Keynote stores character + paragraph + list styles in
``Index/DocumentStylesheet.iwa.yaml``. Each archive has:

  - ``charProperties`` (font, size, color, bold, italic, …)
  - ``paraProperties`` (alignment, line-spacing, indent, …)
  - ``super.parent.identifier`` — points to the parent style (the
    "based on" link, used for inheritance)

A storage's run table (``tableCharStyle.entries`` /
``tableParaStyle.entries``) references styles by identifier. For
each character index N, the effective style is found by:

  1. Look up the nearest ``tableCharStyle`` entry with characterIndex <= N
  2. Resolve its identifier into the doc stylesheet
  3. Walk the ``super.parent.identifier`` chain bottom-up, merging
     ``charProperties`` so child overrides win over parent.

This module gives us:

  - :class:`Stylesheet` — wrapper over the doc stylesheet YAML tree
  - :func:`resolve_char_props_for_run` — merged charProperties at a
    given character index
  - :func:`resolve_para_props_for_run` — same for paragraph props
  - :func:`mutate_char_prop` — set a single charProperty on the
    style at run-index 0 (Step 4c.1 write path)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml


# ============================================================
# Stylesheet
# ============================================================


class Stylesheet:
    """In-memory view of ``Index/DocumentStylesheet.iwa.yaml``.

    Provides O(1) lookup of any style archive by identifier and
    walks the parent chain for inherited properties.
    """

    def __init__(self, yaml_root: dict[str, Any], path: Path):
        self._root = yaml_root
        self._path = path
        self._index: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self._build_index()

    def _build_index(self):
        """Index every archive by identifier → first object."""
        for chunk in self._root.get("chunks", []):
            for arch in chunk.get("archives", []):
                ident = str(arch.get("header", {}).get("identifier"))
                objs = arch.get("objects", [])
                if objs:
                    self._index[ident] = objs[0]

    def get(self, identifier: str | int) -> Optional[dict[str, Any]]:
        return self._index.get(str(identifier))

    def __contains__(self, identifier) -> bool:
        return str(identifier) in self._index

    def __len__(self) -> int:
        return len(self._index)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self):
        self._dirty = True

    def flush(self):
        """Write the stylesheet back to disk if dirty."""
        if not self._dirty:
            return
        with open(self._path, "w") as f:
            yaml.dump(
                self._root,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        self._dirty = False


def load_stylesheet(unpacked_root: Path) -> Optional[Stylesheet]:
    """Load ``Index/DocumentStylesheet.iwa.yaml`` from an unpacked deck."""
    p = unpacked_root / "Index" / "DocumentStylesheet.iwa.yaml"
    if not p.exists():
        return None
    with open(p) as f:
        root = yaml.safe_load(f)
    return Stylesheet(root, p)


# ============================================================
# Style resolution
# ============================================================


def _walk_parent_chain(stylesheet: Stylesheet, archive: dict[str, Any]):
    """Yield archive itself, then ancestors via ``super.parent.identifier``."""
    seen: set[str] = set()
    cur = archive
    while cur is not None:
        # find self id (we don't have it from the archive object, but the
        # caller already gave us a node; we just walk parent links)
        yield cur
        super_ = cur.get("super", {}) or {}
        parent = super_.get("parent")
        if not isinstance(parent, dict):
            break
        pid = str(parent.get("identifier", ""))
        if not pid or pid in seen:
            break
        seen.add(pid)
        cur = stylesheet.get(pid)


def resolve_props(
    stylesheet: Stylesheet, style_id: str | int, which: str = "charProperties"
) -> dict[str, Any]:
    """Resolve the effective ``charProperties`` or ``paraProperties`` for
    a style by walking the parent chain (child overrides win)."""
    archive = stylesheet.get(style_id)
    if archive is None:
        return {}
    # Walk root → leaf so leaf overrides win. We walk leaf → root and
    # accumulate, only setting keys not already set.
    out: dict[str, Any] = {}
    for node in _walk_parent_chain(stylesheet, archive):
        props = node.get(which, {})
        if isinstance(props, dict):
            for k, v in props.items():
                if k not in out:
                    out[k] = v
    return out


def style_id_at_char_index(
    storage_archive: dict[str, Any], char_index: int, which: str = "tableCharStyle"
) -> Optional[str]:
    """Return the style identifier covering ``char_index`` in a storage's
    run table. ``which`` is either ``tableCharStyle`` or ``tableParaStyle``.
    """
    table = storage_archive.get(which)
    if not isinstance(table, dict):
        return None
    entries = table.get("entries", []) or []
    last_id: Optional[str] = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ci = entry.get("characterIndex", 0)
        if ci > char_index:
            break
        obj = entry.get("object")
        if isinstance(obj, dict) and "identifier" in obj:
            last_id = str(obj["identifier"])
    return last_id


def resolve_char_props_for_run(
    stylesheet: Stylesheet, storage_archive: dict[str, Any], char_index: int = 0
) -> dict[str, Any]:
    """Effective charProperties at ``char_index`` in a TSWP.StorageArchive."""
    sid = style_id_at_char_index(storage_archive, char_index, "tableCharStyle")
    if sid is None:
        return {}
    out = resolve_props(stylesheet, sid, "charProperties")
    # Some properties (font, color) often live on the para style too;
    # merge para style as a lower-priority layer.
    pid = style_id_at_char_index(storage_archive, char_index, "tableParaStyle")
    if pid is not None:
        para_chars = resolve_props(stylesheet, pid, "charProperties")
        for k, v in para_chars.items():
            if k not in out:
                out[k] = v
    return out


def resolve_para_props_for_run(
    stylesheet: Stylesheet, storage_archive: dict[str, Any], char_index: int = 0
) -> dict[str, Any]:
    """Effective paraProperties at ``char_index`` in a TSWP.StorageArchive."""
    pid = style_id_at_char_index(storage_archive, char_index, "tableParaStyle")
    if pid is None:
        return {}
    return resolve_props(stylesheet, pid, "paraProperties")


# ============================================================
# Mutation
# ============================================================


def mutate_char_prop(
    stylesheet: Stylesheet,
    storage_archive: dict[str, Any],
    *,
    prop_name: str,
    value: Any,
    char_index: int = 0,
) -> bool:
    """Set a single charProperty on the style covering ``char_index``.

    Step 4c.1 first-cut: mutates the existing referenced archive
    in-place. This works perfectly when the storage's char-style is
    unique to it (override has non-zero ``overrideCount``). For
    storages sharing a base style, mutation may bleed into other text
    blocks — Phase 1.5 will clone the override into a new archive id.

    Returns True if the property was set; False if no style was found.
    """
    sid = style_id_at_char_index(storage_archive, char_index, "tableCharStyle")
    if sid is None:
        # Fall back to the para-style entry (text often uses paragraph-
        # level font / color when there's no per-char override).
        sid = style_id_at_char_index(storage_archive, char_index, "tableParaStyle")
    if sid is None:
        return False
    archive = stylesheet.get(sid)
    if archive is None:
        return False
    props = archive.setdefault("charProperties", {})
    props[prop_name] = value
    archive["overrideCount"] = int(archive.get("overrideCount", 0)) + 1
    stylesheet.mark_dirty()
    return True


def mutate_para_prop(
    stylesheet: Stylesheet,
    storage_archive: dict[str, Any],
    *,
    prop_name: str,
    value: Any,
    char_index: int = 0,
) -> bool:
    """Same as :func:`mutate_char_prop` but for paragraph properties."""
    pid = style_id_at_char_index(storage_archive, char_index, "tableParaStyle")
    if pid is None:
        return False
    archive = stylesheet.get(pid)
    if archive is None:
        return False
    props = archive.setdefault("paraProperties", {})
    props[prop_name] = value
    archive["overrideCount"] = int(archive.get("overrideCount", 0)) + 1
    stylesheet.mark_dirty()
    return True
