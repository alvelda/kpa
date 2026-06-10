"""
kpa.layout — Slide layout/structure (Step 4c.3)
================================================

Z-ordering helpers and Group proxy. Z-order lives on
``KN.SlideArchive.drawablesZOrder`` as a list of ``{identifier: <id>}``
refs. The first entry renders at the back; the last entry renders on top.

Group archives (``TSD.GroupArchive``) are sibling archives in the slide
YAML — same pattern as KN.BuildArchive. They contain a ``children`` list
of drawable refs (older builds may use ``contents``). The proxy supports
both.

SVEF has 43 group instances; NCI has 3; test1 has 1. The correct pbtype
is ``TSD.GroupArchive`` (not ``KN.GroupArchive`` — that was a wrong guess
in the 4c.3 first pass and yielded an always-empty `Slide.groups`).
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
    """A :class:`TSD.GroupArchive` instance on a slide.

    Read access in 4c.3.2; the escape hatch
    (``group.raw_get`` / ``group.raw_set``) is available for advanced
    mutation. Typed write accessors (``add_child`` / ``remove_child`` /
    ``set_position`` / ``set_size``) added in 4c.3.2.
    """

    def __init__(self, *, slide: "Slide", archive: dict[str, Any], archive_id: str):
        self._slide = slide
        self._archive = archive
        self._archive_id = archive_id

    @property
    def archive_id(self) -> str:
        return self._archive_id

    def _children_key(self) -> str:
        """Whichever child list key the archive actually uses.

        Apple's current encoder writes ``children`` for TSD.GroupArchive.
        Some older builds use ``contents``. We honor whichever is
        already present; default to ``children`` for new entries.
        """
        if "children" in self._archive:
            return "children"
        if "contents" in self._archive:
            return "contents"
        return "children"

    def _children_list(self) -> list:
        """Mutable child-ref list, creating if missing."""
        key = self._children_key()
        lst = self._archive.get(key)
        if not isinstance(lst, list):
            lst = []
            self._archive[key] = lst
        return lst

    @property
    def children_ids(self) -> tuple[str, ...]:
        """Archive ids of the group's children, in order."""
        out: list[str] = []
        for item in self._children_list():
            if isinstance(item, dict) and "identifier" in item:
                out.append(str(item["identifier"]))
        return tuple(out)

    # ---- geometry passthroughs (TSD shape base) ----

    def _super(self) -> dict:
        s = self._archive.get("super")
        if not isinstance(s, dict):
            s = {}
            self._archive["super"] = s
        return s

    def _geometry(self) -> dict:
        sup = self._super()
        g = sup.get("geometry")
        if not isinstance(g, dict):
            g = {}
            sup["geometry"] = g
        return g

    @property
    def position(self) -> tuple[float, float]:
        pos = self._geometry().get("position") or {}
        return (float(pos.get("x", 0.0)), float(pos.get("y", 0.0)))

    @property
    def size(self) -> tuple[float, float]:
        sz = self._geometry().get("size") or {}
        return (float(sz.get("width", 0.0)), float(sz.get("height", 0.0)))

    @property
    def angle(self) -> float:
        return float(self._geometry().get("angle", 0.0))

    def set_position(self, x: float, y: float) -> None:
        g = self._geometry()
        g["position"] = {"x": float(x), "y": float(y)}
        self._slide._mark_dirty()

    def set_size(self, width: float, height: float) -> None:
        g = self._geometry()
        g["size"] = {"width": float(width), "height": float(height)}
        self._slide._mark_dirty()

    def move(self, dx: float = 0.0, dy: float = 0.0) -> None:
        x, y = self.position
        self.set_position(x + float(dx), y + float(dy))

    # ---- child membership writes ----

    def add_child(self, shape) -> None:
        """Append a drawable's id to the group's children list."""
        cid = _resolve_shape_id(shape)
        if not cid:
            raise ValueError("add_child requires a shape with an archive id")
        lst = self._children_list()
        # idempotent
        for item in lst:
            if isinstance(item, dict) and str(item.get("identifier")) == cid:
                return
        lst.append({"identifier": cid})
        self._slide._mark_dirty()

    def remove_child(self, shape) -> bool:
        """Remove a drawable from the group. Returns True if removed."""
        cid = _resolve_shape_id(shape)
        lst = self._children_list()
        for i, item in enumerate(lst):
            if isinstance(item, dict) and str(item.get("identifier")) == cid:
                del lst[i]
                self._slide._mark_dirty()
                return True
        return False

    def set_children(self, shapes) -> None:
        """Replace the child list with the given shapes (in order)."""
        key = self._children_key()
        new_list = [{"identifier": _resolve_shape_id(s)} for s in shapes]
        self._archive[key] = new_list
        self._slide._mark_dirty()

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
