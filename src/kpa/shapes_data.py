"""
kpa.shapes_data
================

Step 4c.6 (first pass) — read-only proxies for data shapes:

  * :class:`Chart` — wraps :class:`TSCH.ChartDrawableArchive`
  * :class:`Table` — wraps :class:`TST.TableInfoArchive`

Both proxies inherit from :class:`kpa.escape.RawArchiveMixin` so any
field (including the bracketed ``[TSCH.*]`` / ``[TST.*]`` extension
keys that hold the bulk of the schema) is reachable via
``raw_get``/``raw_set``.

Why read-only first
-------------------
TSCH chart schemas are entirely extension-driven (every TSCH archive
exposes only ``super`` as a real field; the data lives in bracketed
extension keys like ``[TSCH.ChartArchive.unity]``). Series data,
axis configuration, and chart kind all live behind extension
boundaries that need careful handling. Mutating those without a
sample deck to verify against is asking for silent corruption.

The first pass therefore exposes:

  * Stable identifier + pbtype for discovery
  * Geometry passthrough (so layout tools can move charts/tables)
  * Aspect-ratio + caption flags (the ``super.super`` shared base)
  * Universal escape hatch (inherited from RawArchiveMixin) for any
    other read

Writes are deferred to **4c.6.2** once we have a synthetic test deck
with a known chart kind/series to round-trip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from kpa.escape import RawArchiveMixin

if TYPE_CHECKING:
    from kpa.objects import Slide


class _DataShapeBase(RawArchiveMixin):
    """Shared ``super.super``/``super`` walking helpers for chart and
    table proxies.

    Charts: ``TSCH.ChartDrawableArchive`` → ``super`` (TSD shape base)
    Tables: ``TST.TableInfoArchive`` → ``super`` (TSD shape base)

    Both inherit from the same TSD drawable base so the geometry path
    is identical.
    """

    def __init__(self, *, slide: "Slide", archive: dict[str, Any], archive_id: str):
        self._slide = slide
        self._archive = archive
        self._archive_id = archive_id

    # ---- RawArchiveMixin hooks ----

    def _raw_archive_root(self) -> dict:
        return self._archive

    def _raw_mark_dirty(self) -> None:
        self._slide._mark_dirty()

    # ---- common metadata ----

    @property
    def archive_id(self) -> str:
        return self._archive_id

    def __repr__(self) -> str:
        return f"<{type(self).__name__} #{self._archive_id}>"

    # ---- helpers ----

    def _shape_base(self) -> dict[str, Any]:
        """The ``super`` block (TSD shape base) where geometry lives."""
        return self._archive.get("super") or {}


class Chart(_DataShapeBase):
    """Read-only proxy for a :class:`TSCH.ChartDrawableArchive` on a
    slide.

    The chart's full data (kind, series, axes, legend) is reachable
    via the escape hatch:

    .. code-block:: python

        chart.raw_pbtype()                                  # 'TSCH.ChartDrawableArchive'
        chart.raw_keys()                                    # ['_pbtype', 'super', '[TSCH.ChartArchive.unity]']
        chart.raw_get('[TSCH.ChartArchive.unity]')          # the chart preset extension dict

    Geometry is exposed as ``position``, ``size``, and ``angle``
    convenience reads (matching :class:`Image`).
    """

    PBTYPE = "TSCH.ChartDrawableArchive"

    # ---- geometry passthrough (read-only) ----

    def _geometry(self) -> Optional[dict[str, Any]]:
        return self._shape_base().get("geometry")

    @property
    def position(self) -> Optional[tuple[float, float]]:
        g = self._geometry()
        if g is None:
            return None
        p = g.get("position") or {}
        if "x" in p and "y" in p:
            return (float(p["x"]), float(p["y"]))
        return None

    @property
    def size(self) -> Optional[tuple[float, float]]:
        g = self._geometry()
        if g is None:
            return None
        s = g.get("size") or {}
        if "width" in s and "height" in s:
            return (float(s["width"]), float(s["height"]))
        return None

    @property
    def angle(self) -> float:
        g = self._geometry() or {}
        return float(g.get("angle", 0.0) or 0.0)

    @property
    def aspect_ratio_locked(self) -> bool:
        return bool(self._shape_base().get("aspectRatioLocked", False))

    @property
    def locked(self) -> bool:
        return bool(self._shape_base().get("locked", False))

    @property
    def caption_hidden(self) -> bool:
        return bool(self._shape_base().get("captionHidden", True))

    # ---- chart-specific introspection ----

    @property
    def has_chart_unity(self) -> bool:
        """True if the canonical ``[TSCH.ChartArchive.unity]`` extension
        block is present."""
        return "[TSCH.ChartArchive.unity]" in self._archive

    @property
    def chart_unity_keys(self) -> tuple[str, ...]:
        """Sub-extension keys inside ``[TSCH.ChartArchive.unity]``.

        Useful for discovering what TSCH presets a chart carries
        (e.g. ``[TSCH.ChartPreserveAppearanceForPresetArchive.*]``).
        """
        u = self._archive.get("[TSCH.ChartArchive.unity]") or {}
        return tuple(u.keys())


class Table(_DataShapeBase):
    """Read-only proxy for a :class:`TST.TableInfoArchive` on a slide.

    First-pass scope: identifier + geometry passthrough + escape
    hatch. Cell read/write API deferred to 4c.6.2 (heavy schema, no
    sample deck instance to verify against in this repo's SVEF/NCI
    fixtures).
    """

    PBTYPE = "TST.TableInfoArchive"

    # ---- geometry passthrough (mirrors Chart) ----

    def _geometry(self) -> Optional[dict[str, Any]]:
        return self._shape_base().get("geometry")

    @property
    def position(self) -> Optional[tuple[float, float]]:
        g = self._geometry()
        if g is None:
            return None
        p = g.get("position") or {}
        if "x" in p and "y" in p:
            return (float(p["x"]), float(p["y"]))
        return None

    @property
    def size(self) -> Optional[tuple[float, float]]:
        g = self._geometry()
        if g is None:
            return None
        s = g.get("size") or {}
        if "width" in s and "height" in s:
            return (float(s["width"]), float(s["height"]))
        return None

    @property
    def angle(self) -> float:
        g = self._geometry() or {}
        return float(g.get("angle", 0.0) or 0.0)

    @property
    def aspect_ratio_locked(self) -> bool:
        return bool(self._shape_base().get("aspectRatioLocked", False))

    @property
    def locked(self) -> bool:
        return bool(self._shape_base().get("locked", False))


# =========== document-level stylesheet introspection ===========


def list_table_style_archive_ids(deck) -> tuple[str, ...]:
    """Return the identifiers of every :class:`TST.TableStyleArchive`
    in the deck's DocumentStylesheet.

    These are the named table styles that appear in Keynote's style
    chooser. Useful for brand-style validators (4c.8) and for
    debugging which styles are referenced by table instances.
    """
    sheet = deck.stylesheet
    if sheet is None:
        return tuple()
    return tuple(
        ident for ident, _arch in sheet.iter_by_pbtype("TST.TableStyleArchive")
    )


def list_chart_style_archive_ids(deck) -> tuple[str, ...]:
    """Return the identifiers of every :class:`TSCH.ChartStyleArchive`
    in the deck's DocumentStylesheet."""
    sheet = deck.stylesheet
    if sheet is None:
        return tuple()
    return tuple(
        ident for ident, _arch in sheet.iter_by_pbtype("TSCH.ChartStyleArchive")
    )
