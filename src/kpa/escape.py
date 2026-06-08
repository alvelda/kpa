"""
kpa.escape — Universal escape hatch for raw archive access (Step 4c.7)
=======================================================================

The kpa API covers the editable surface for ~70% of Keynote's protobuf
schema (Phase 1 target). For everything not yet wrapped — and for
agent-defined experimental edits — every proxy exposes:

  obj.raw_archive()        -> dict   (the underlying YAML/protobuf node)
  obj.raw_get(path)        -> Any    (read a deep path)
  obj.raw_set(path, value) -> self   (write a deep path)
  obj.raw_keys(path="")    -> list   (introspect keys at a path)
  obj.raw_dump(path="", maxdepth=3) -> dict (pretty-printable view)

**Path syntax:**
  - Dot-separated for dict keys:  ``"super.geometry.angle"``
  - Bracketed for list indices:   ``"super.objects[0].pbtype"``
  - Mixed:                        ``"text[0].runs[1].font"``
  - Empty path (``""``) means the archive itself

This is intentionally a thin wrapper around the raw schema. Use it
when the typed API doesn't yet cover a property; expect the property
name to be the protobuf field name verbatim. Once an escape-hatch
usage stabilizes, promote it to a typed accessor in a future kpa
release.

**Safety:** raw_set marks the owning slide (or deck) as dirty so
mutations flush on save(). Use ``raw_archive()`` for read-only
inspection; modify the returned dict at your own risk (mark dirty
explicitly by calling ``raw_set`` instead).
"""

from __future__ import annotations

import re
from typing import Any, Optional


# ---------- path parser ----------

# Match either a bare key (until '.' or '[') or a [index] segment.
_SEGMENT_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def _parse_path(path: str) -> list:
    """Parse a path string into a list of (kind, key) tuples.

    kind is 'key' for dict keys (key=str) or 'idx' for list indices
    (key=int). An empty path yields an empty list.
    """
    if not path:
        return []
    out = []
    pos = 0
    while pos < len(path):
        m = _SEGMENT_RE.match(path, pos)
        if not m:
            raise ValueError(f"Invalid path segment at position {pos} in {path!r}")
        if m.group(1) is not None:
            out.append(("key", m.group(1)))
        else:
            out.append(("idx", int(m.group(2))))
        pos = m.end()
        # Skip dot separator between key segments
        if pos < len(path) and path[pos] == ".":
            pos += 1
    return out


# ---------- walkers ----------


def deep_get(root: Any, path: str, default: Any = None) -> Any:
    """Walk path through nested dicts/lists; return default on miss."""
    cur = root
    for kind, key in _parse_path(path):
        if kind == "key":
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        else:  # idx
            if not isinstance(cur, list) or key >= len(cur) or key < -len(cur):
                return default
            cur = cur[key]
    return cur


def deep_set(root: Any, path: str, value: Any) -> None:
    """Walk path through nested dicts/lists and set the final segment to
    value. Creates missing dict keys; raises ValueError on a missing
    list index or type mismatch.
    """
    segs = _parse_path(path)
    if not segs:
        raise ValueError("Cannot set empty path; pass a non-empty path or modify root directly")
    cur = root
    for i, (kind, key) in enumerate(segs[:-1]):
        if kind == "key":
            if not isinstance(cur, dict):
                raise ValueError(
                    f"Path {path!r} expects dict at segment {i} but got {type(cur).__name__}"
                )
            if key not in cur:
                # Auto-create as dict for missing intermediate keys
                cur[key] = {}
            cur = cur[key]
        else:
            if not isinstance(cur, list):
                raise ValueError(
                    f"Path {path!r} expects list at segment {i} but got {type(cur).__name__}"
                )
            if key >= len(cur) or key < -len(cur):
                raise ValueError(
                    f"Path {path!r}: list index {key} out of range (len={len(cur)})"
                )
            cur = cur[key]
    last_kind, last_key = segs[-1]
    if last_kind == "key":
        if not isinstance(cur, dict):
            raise ValueError(
                f"Path {path!r} expects dict at final segment but got {type(cur).__name__}"
            )
        cur[last_key] = value
    else:
        if not isinstance(cur, list):
            raise ValueError(
                f"Path {path!r} expects list at final segment but got {type(cur).__name__}"
            )
        if last_key >= len(cur) or last_key < -len(cur):
            raise ValueError(
                f"Path {path!r}: final list index {last_key} out of range (len={len(cur)})"
            )
        cur[last_key] = value


def keys_at(root: Any, path: str = "") -> list:
    """Return the keys (for dicts) or indices (for lists) at the path."""
    node = deep_get(root, path)
    if isinstance(node, dict):
        return list(node.keys())
    if isinstance(node, list):
        return list(range(len(node)))
    return []


def truncate_view(node: Any, maxdepth: int = 3, _depth: int = 0) -> Any:
    """Produce a depth-limited pretty view of nested structures."""
    if _depth >= maxdepth:
        if isinstance(node, dict):
            return f"<dict {len(node)} keys: {list(node.keys())[:5]}>"
        if isinstance(node, list):
            return f"<list {len(node)}>"
        return node
    if isinstance(node, dict):
        return {k: truncate_view(v, maxdepth, _depth + 1) for k, v in node.items()}
    if isinstance(node, list):
        return [truncate_view(v, maxdepth, _depth + 1) for v in node[:10]]
    return node


# ---------- mixin ----------


class RawArchiveMixin:
    """Adds raw_archive / raw_get / raw_set / raw_keys / raw_dump to any
    proxy that implements two hook methods:

      _raw_archive_root() -> dict
          Return the archive dict this proxy wraps.

      _raw_mark_dirty() -> None
          Mark the owning container (slide / deck) as needing a save().
    """

    # Subclasses must override these.
    def _raw_archive_root(self) -> dict:
        raise NotImplementedError(
            f"{type(self).__name__} must implement _raw_archive_root()"
        )

    def _raw_mark_dirty(self) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} must implement _raw_mark_dirty()"
        )

    # ---- public API ----

    def raw_archive(self) -> dict:
        """Return the underlying archive dict (live reference)."""
        return self._raw_archive_root()

    def raw_get(self, path: str = "", default: Any = None) -> Any:
        """Read a value at a deep path. Returns default on miss.

        Examples:
            tb.raw_get("super.geometry.angle")
            mv.raw_get("naturalSize.width")
            b.raw_get("attributes.animationAttributes.effect")
        """
        return deep_get(self._raw_archive_root(), path, default)

    def raw_set(self, path: str, value: Any) -> "RawArchiveMixin":
        """Set a value at a deep path; marks the slide/deck dirty.

        Chainable. Auto-creates missing dict intermediates; raises on
        missing list indices or type mismatches.
        """
        deep_set(self._raw_archive_root(), path, value)
        self._raw_mark_dirty()
        return self

    def raw_keys(self, path: str = "") -> list:
        """Keys (dict) or indices (list) at the given path."""
        return keys_at(self._raw_archive_root(), path)

    def raw_dump(self, path: str = "", maxdepth: int = 3) -> Any:
        """Depth-limited pretty view for inspection. Safe to print."""
        node = self.raw_get(path) if path else self._raw_archive_root()
        return truncate_view(node, maxdepth)

    def raw_pbtype(self) -> Optional[str]:
        """The protobuf type string of this archive (e.g. ``TSD.MovieArchive``)."""
        root = self._raw_archive_root()
        if isinstance(root, dict):
            v = root.get("_pbtype")
            return str(v) if v is not None else None
        return None
