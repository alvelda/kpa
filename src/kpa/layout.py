"""
kpa.layout — Slide layout/structure (Step 4c.3)
================================================

Z-ordering helpers and Group proxy. Z-order lives on
``KN.SlideArchive.drawablesZOrder`` as a list of ``{identifier: <id>}``
refs. The first entry renders at the back; the last entry renders on top.

Group archives (``KN.GroupArchive``) are sibling archives in the slide
YAML — same pattern as KN.BuildArchive. They contain a ``contents`` list
of drawable refs. Neither SVEF nor NCI use groups, so write support is
deferred; we provide a read-only :class:`Group` proxy + raw-introspection
helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from kpa.escape import RawArchiveMixin

if TYPE_CHECKING:
    from kpa.objects import Slide


# ============================================================
# Z-order helpers
# ============================================================


def _resolve_shape_id(shape) -> str:
    """Resolve a shape-like input (TextBlock, Image, str, int, dict) to its
    archive id string."""
    if isinstance(shape, dict) and "identifier" in shape:
        return str(shape["identifier"])
    for attr in ("_archive_id", "_shape_id"):
        v = getattr(shape, attr, None)
        if v is not None:
            return str(v)
    return str(shape)


def _zorder_list(slide_archive: dict) -> list[dict]:
    """Get the mutable drawablesZOrder list, creating if missing."""
    zo = slide_archive.get("drawablesZOrder")
    if not isinstance(zo, list):
        zo = []
        slide_archive["drawablesZOrder"] = zo
    return zo


def _zorder_index(zorder: list[dict], target_id: str) -> int:
    """Index of target_id in zorder list, or -1 if absent."""
    for i, item in enumerate(zorder):
        if isinstance(item, dict) and str(item.get("identifier")) == target_id:
            return i
    return -1


# ============================================================
# Group proxy (read-only in 4c.3)
# ============================================================


class Group(RawArchiveMixin):
    """A :class:`KN.GroupArchive` instance on a slide.

    Read-only in Step 4c.3. The escape hatch
    (``group.raw_get`` / ``group.raw_set``) is available for advanced
    mutation; promote to typed accessors when patterns crystallize.
    """

    def __init__(self, *, slide: "Slide", archive: dict[str, Any], archive_id: str):
        self._slide = slide
        self._archive = archive
        self._archive_id = archive_id

    @property
    def archive_id(self) -> str:
        return self._archive_id

    @property
    def children_ids(self) -> tuple[str, ...]:
        """Archive ids of the group's children, in order."""
        contents = self._archive.get("contents") or self._archive.get("children") or []
        out: list[str] = []
        if isinstance(contents, list):
            for item in contents:
                if isinstance(item, dict) and "identifier" in item:
                    out.append(str(item["identifier"]))
        return tuple(out)

    @property
    def children(self) -> tuple:
        """Resolved child proxies (TextBlock / Image) for known kinds.

        Unknown kinds are skipped — agents can drop to :meth:`raw_get`
        on the slide to access them.
        """
        out: list = []
        for cid in self.children_ids:
            obj = self._slide._archive_object(cid)
            if obj is None:
                continue
            pbtype = obj.get("_pbtype", "")
            if pbtype in ("TSWP.ShapeInfoArchive", "KN.PlaceholderArchive"):
                tb = self._slide._make_text_block(cid, role="text")
                if tb is not None:
                    out.append(tb)
            elif pbtype in ("TSD.ImageArchive", "TSD.MediaArchive", "TSD.MovieArchive"):
                # Resolve via slide.images then filter
                for img in self._slide.images:
                    if img._archive_id == cid:
                        out.append(img)
                        break
        return tuple(out)

    # --- RawArchiveMixin hooks ---

    def _raw_archive_root(self) -> dict:
        return self._archive

    def _raw_mark_dirty(self) -> None:
        self._slide._mark_dirty()

    def __repr__(self):
        return (
            f"<Group id={self._archive_id} children={len(self.children_ids)}>"
        )
