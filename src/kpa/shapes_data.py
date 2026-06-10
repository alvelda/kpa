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

from pathlib import Path
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
    """Proxy for a :class:`TSCH.ChartDrawableArchive` on a slide.

    The chart's full data (kind, series, axes, legend) is reachable
    via the escape hatch:

    .. code-block:: python

        chart.raw_pbtype()                                  # 'TSCH.ChartDrawableArchive'
        chart.raw_keys()                                    # ['_pbtype', 'super', '[TSCH.ChartArchive.unity]']
        chart.raw_get('[TSCH.ChartArchive.unity]')          # the chart preset extension dict

    Geometry is exposed as ``position``, ``size``, and ``angle``
    convenience reads + setters (matching :class:`Image`).

    Step 4c.6.2 adds typed write accessors over the most-asked-for
    chart data: type, style, column names, row names, and per-series
    numeric values. The grid schema is

    .. code-block:: text

        unity['grid'] = {
            'columnName': [str, ...]  # x-axis category labels
            'rowName':    [str, ...]  # one entry per series
            'gridRow':    [{ 'value': [{ 'numericValue': float }, ... ] }, ... ]
        }

    Series order matches ``rowName``; value count per row must match
    ``len(columnName)``.
    """

    PBTYPE = "TSCH.ChartDrawableArchive"

    # ---- geometry passthrough ----

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

    # ---- geometry setters (4c.6.2) ----

    def set_position(self, x: float, y: float) -> "Chart":
        g = self._geometry()
        if g is None:
            raise ValueError("chart has no geometry block")
        g.setdefault("position", {})
        g["position"]["x"] = float(x)
        g["position"]["y"] = float(y)
        self._slide._mark_dirty()
        return self

    def set_size(self, width: float, height: float) -> "Chart":
        g = self._geometry()
        if g is None:
            raise ValueError("chart has no geometry block")
        g.setdefault("size", {})
        g["size"]["width"] = float(width)
        g["size"]["height"] = float(height)
        self._slide._mark_dirty()
        return self

    def move(self, dx: float = 0.0, dy: float = 0.0) -> "Chart":
        p = self.position
        if p is None:
            raise ValueError("chart has no geometry position")
        return self.set_position(p[0] + dx, p[1] + dy)

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

    # ---- chart data accessors (4c.6.2) ----

    _UNITY_KEY = "[TSCH.ChartArchive.unity]"

    def _unity(self) -> dict[str, Any]:
        """Return the live unity extension dict, creating it if absent."""
        u = self._archive.get(self._UNITY_KEY)
        if u is None:
            u = {}
            self._archive[self._UNITY_KEY] = u
        return u

    def _grid(self) -> dict[str, Any]:
        """Return the live grid dict, creating it if absent."""
        u = self._unity()
        g = u.get("grid")
        if g is None:
            g = {}
            u["grid"] = g
        return g

    @property
    def chart_type(self) -> Optional[str]:
        """Chart kind enum, e.g. ``'lineChartType2D'``, ``'barChartType2D'``,
        ``'columnChartType2D'``, ``'pieChartType2D'``, ``'areaChartType2D'``,
        ``'scatterChartType2D'``. ``None`` if the chart has no unity block."""
        u = self._archive.get(self._UNITY_KEY)
        if not isinstance(u, dict):
            return None
        v = u.get("chartType")
        return str(v) if v is not None else None

    @chart_type.setter
    def chart_type(self, value: str) -> None:
        self.set_chart_type(value)

    def set_chart_type(self, value: str) -> "Chart":
        """Set the chart kind. The value is written verbatim; Keynote
        accepts arbitrary enum strings from the TSCH schema."""
        if not isinstance(value, str) or not value:
            raise ValueError(f"chart_type must be a non-empty string, got {value!r}")
        self._unity()["chartType"] = value
        self._slide._mark_dirty()
        return self

    @property
    def chart_style_id(self) -> Optional[str]:
        """Stylesheet identifier referenced by ``chartStyle``."""
        u = self._archive.get(self._UNITY_KEY)
        if not isinstance(u, dict):
            return None
        cs = u.get("chartStyle")
        if isinstance(cs, dict):
            ident = cs.get("identifier")
            return str(ident) if ident is not None else None
        return None

    @chart_style_id.setter
    def chart_style_id(self, value: str) -> None:
        self.set_chart_style_id(value)

    def set_chart_style_id(self, value: str) -> "Chart":
        """Point ``chartStyle`` at the given stylesheet identifier."""
        if value is None:
            raise ValueError("chart_style_id may not be None")
        self._unity()["chartStyle"] = {"identifier": str(value)}
        self._slide._mark_dirty()
        return self

    @property
    def column_names(self) -> tuple[str, ...]:
        """X-axis category labels."""
        g = self._archive.get(self._UNITY_KEY, {}).get("grid", {}) if isinstance(
            self._archive.get(self._UNITY_KEY), dict
        ) else {}
        cols = g.get("columnName") or []
        return tuple(str(c) for c in cols)

    @column_names.setter
    def column_names(self, values) -> None:
        self.set_column_names(values)

    def set_column_names(self, values) -> "Chart":
        """Replace the x-axis category labels.

        The new list must have the same length as the existing
        ``columnName`` (otherwise per-series values would silently
        misalign). Use :meth:`resize_grid` to change shape.
        """
        new = [str(v) for v in values]
        cur = list(self.column_names)
        if cur and len(new) != len(cur):
            raise ValueError(
                f"column_names length mismatch: have {len(cur)}, got {len(new)}; "
                f"call resize_grid(...) first to change shape"
            )
        self._grid()["columnName"] = new
        self._slide._mark_dirty()
        return self

    @property
    def row_names(self) -> tuple[str, ...]:
        """Series labels (one entry per series)."""
        g = self._archive.get(self._UNITY_KEY, {}).get("grid", {}) if isinstance(
            self._archive.get(self._UNITY_KEY), dict
        ) else {}
        rows = g.get("rowName") or []
        return tuple(str(r) for r in rows)

    @row_names.setter
    def row_names(self, values) -> None:
        self.set_row_names(values)

    def set_row_names(self, values) -> "Chart":
        """Replace the series labels.

        Length must match the existing ``gridRow`` count.
        """
        new = [str(v) for v in values]
        cur = list(self.row_names)
        if cur and len(new) != len(cur):
            raise ValueError(
                f"row_names length mismatch: have {len(cur)}, got {len(new)}"
            )
        self._grid()["rowName"] = new
        self._slide._mark_dirty()
        return self

    def series_count(self) -> int:
        g = self._archive.get(self._UNITY_KEY, {}).get("grid", {}) if isinstance(
            self._archive.get(self._UNITY_KEY), dict
        ) else {}
        rows = g.get("gridRow") or []
        return len(rows)

    def series_values(self, row_index: int = 0) -> tuple[Optional[float], ...]:
        """Return the numeric values for series ``row_index``.

        Cells without a ``numericValue`` (e.g. blanks) come back as
        ``None``.
        """
        g = self._archive.get(self._UNITY_KEY, {}).get("grid", {}) if isinstance(
            self._archive.get(self._UNITY_KEY), dict
        ) else {}
        rows = g.get("gridRow") or []
        if not (0 <= row_index < len(rows)):
            raise IndexError(
                f"row_index {row_index} out of range (0..{len(rows) - 1})"
            )
        out: list[Optional[float]] = []
        for cell in rows[row_index].get("value", []) or []:
            if isinstance(cell, dict) and "numericValue" in cell:
                out.append(float(cell["numericValue"]))
            else:
                out.append(None)
        return tuple(out)

    def set_series_values(self, values, row_index: int = 0) -> "Chart":
        """Replace the numeric values for series ``row_index``.

        ``None`` entries write a blank cell (no ``numericValue`` key).
        Length must match the column count.
        """
        n_cols = len(self.column_names)
        new = list(values)
        if n_cols and len(new) != n_cols:
            raise ValueError(
                f"series length mismatch: have {n_cols} columns, got {len(new)}"
            )
        rows = self._grid().setdefault("gridRow", [])
        # Pad rows if row_index goes past current end (rare; usually
        # callers add a new series via add_series).
        while len(rows) <= row_index:
            rows.append({"value": []})
        cells: list[dict[str, Any]] = []
        for v in new:
            if v is None:
                cells.append({})
            else:
                cells.append({"numericValue": float(v)})
        rows[row_index]["value"] = cells
        self._slide._mark_dirty()
        return self

    # ---- isDirty hint (force Keynote to recompute on next open) ----

    def mark_dirty_for_recompute(self) -> "Chart":
        """Set the unity ``isDirty`` flag so Keynote re-runs the chart
        layout engine on next open. Useful after large data swaps."""
        self._unity()["isDirty"] = True
        self._slide._mark_dirty()
        return self


class Table(_DataShapeBase):
    """Proxy for a :class:`TST.TableInfoArchive` on a slide.

    First-pass scope: identifier + geometry passthrough + geometry
    mutation + ``tableModel`` / ``summaryModel`` refs + escape hatch.

    Cell read/write goes through ``TST.TableModelArchive.baseDataStore``
    (tile-archived cell payloads). Those are heavy to decode safely;
    we provide the geometry path now and surface the reference ids so
    agents can drop into the escape hatch for cell-level work until a
    typed cell API lands.

    Note (4c.6.2-tables): on-slide tables ship their
    ``TST.TableInfoArchive`` in ``CalculationEngine.iwa.yaml`` rather
    than the slide's own YAML. ``Slide.tables`` finds them via the
    deck-wide ``_by_parent_index``. ``Table._aux_yaml_path`` (set by
    ``Slide.tables``) records the source file so geometry mutations
    can mark it dirty.
    """

    PBTYPE = "TST.TableInfoArchive"

    # Set by Slide.tables when the table archive lives in a sibling
    # Index file (e.g. CalculationEngine.iwa.yaml).
    _aux_yaml_path: Optional[Path] = None

    # ---- geometry setters ----

    def _mark_dirty_cross_file(self) -> None:
        """Mark the slide and (when present) the sibling file dirty."""
        self._slide._mark_dirty()
        if self._aux_yaml_path is not None:
            deck = self._slide._deck
            deck._mark_aux_dirty(self._aux_yaml_path)

    def set_position(self, x: float, y: float) -> "Table":
        g = self._shape_base().setdefault("geometry", {})
        g["position"] = {"x": float(x), "y": float(y)}
        self._mark_dirty_cross_file()
        return self

    def set_size(self, width: float, height: float) -> "Table":
        g = self._shape_base().setdefault("geometry", {})
        g["size"] = {"width": float(width), "height": float(height)}
        self._mark_dirty_cross_file()
        return self

    def move(self, dx: float = 0.0, dy: float = 0.0) -> "Table":
        x, y = self.position or (0.0, 0.0)
        return self.set_position(x + float(dx), y + float(dy))

    # ---- model references (for escape-hatch cell work) ----

    @property
    def table_model_id(self) -> Optional[str]:
        """Identifier of the :class:`TST.TableModelArchive` that holds
        this table's cells (in CalculationEngine.iwa.yaml)."""
        ref = self._archive.get("tableModel")
        if isinstance(ref, dict):
            v = ref.get("identifier")
            return str(v) if v is not None else None
        return None

    @property
    def summary_model_id(self) -> Optional[str]:
        """Identifier of the :class:`TST.SummaryCellVendorArchive`
        backing this table's summary (if any)."""
        ref = self._archive.get("summaryModel")
        if isinstance(ref, dict):
            v = ref.get("identifier")
            return str(v) if v is not None else None
        return None

    # ---- cell access (TST tile codec) ----

    def _table_model(self) -> Optional[dict]:
        """Resolve the TableModelArchive object dict."""
        tm = self.table_model_id
        if tm is None:
            return None
        deck = self._slide._deck
        res = deck._archive_by_id(tm)
        if res is None:
            return None
        _yml, _arch, obj = res
        return obj

    def _strings_archive(self) -> Optional[tuple["Path", dict, dict]]:
        """Resolve the stringTable archive (yaml_path, archive, object)."""
        tm = self._table_model()
        if tm is None:
            return None
        st_ref = tm.get("baseDataStore", {}).get("stringTable", {})
        st_id = st_ref.get("identifier")
        if st_id is None:
            return None
        return self._slide._deck._archive_by_id(str(st_id))

    def _tile_archive(self) -> Optional[tuple["Path", dict, dict]]:
        """Resolve the (first) tile archive. Currently tables in our
        corpus all fit in a single tile (tileSize=256). Multi-tile
        tables would need column/row -> tile mapping."""
        tm = self._table_model()
        if tm is None:
            return None
        tiles = tm.get("baseDataStore", {}).get("tiles", {}).get("tiles", [])
        if not tiles:
            return None
        ref = tiles[0].get("tile", {})
        tid = ref.get("identifier")
        if tid is None:
            return None
        return self._slide._deck._archive_by_id(str(tid))

    @property
    def num_rows(self) -> int:
        tm = self._table_model()
        return int(tm.get("numberOfRows", 0)) if tm else 0

    @property
    def num_cols(self) -> int:
        tm = self._table_model()
        return int(tm.get("numberOfColumns", 0)) if tm else 0

    def _strings_map(self) -> dict[int, str]:
        res = self._strings_archive()
        if res is None:
            return {}
        _y, _a, obj = res
        return {int(e["key"]): e.get("string", "") for e in obj.get("entries", []) if "key" in e}

    def cell(self, row: int, col: int):
        """Return the decoded :class:`Cell` at (row, col), or None for
        a structurally empty cell.

        Raises IndexError on out-of-range indices.
        """
        from kpa.tst_cells import decode_row
        tile_res = self._tile_archive()
        if tile_res is None:
            raise RuntimeError("table has no tile data")
        _y, _a, tile_obj = tile_res
        rows = tile_obj.get("rowInfos", [])
        # rows are indexed by tileRowIndex; many decks have them sorted
        # by tileRowIndex already, but be defensive.
        target = None
        for ri in rows:
            if int(ri.get("tileRowIndex", -1)) == row:
                target = ri
                break
        if target is None:
            raise IndexError(f"row {row} not present in tile (rows={len(rows)})")
        decoded = decode_row(target, self._strings_map())
        if col < 0 or col >= len(decoded):
            raise IndexError(f"col {col} out of range (row has {len(decoded)} cells)")
        return decoded[col]

    def values(self) -> list[list]:
        """Return the table as a 2-D list of decoded cell values.
        Each entry is either the typed Python value (str | int) or
        ``None`` for empty cells. ``raw``-typed cells (unparsed format
        like formula or date) surface as raw bytes — agents should
        check the cell's ``.kind`` via :meth:`cell` for those."""
        from kpa.tst_cells import decode_row
        tile_res = self._tile_archive()
        if tile_res is None:
            return []
        _y, _a, tile_obj = tile_res
        strings = self._strings_map()
        # Sort rowInfos by tileRowIndex for stable output
        rows = sorted(
            tile_obj.get("rowInfos", []),
            key=lambda r: int(r.get("tileRowIndex", 0)),
        )
        out: list[list] = []
        for ri in rows:
            cells = decode_row(ri, strings)
            out.append([c.value if c is not None else None for c in cells])
        return out

    def _row_info_for(self, row: int) -> Optional[dict]:
        tile_res = self._tile_archive()
        if tile_res is None:
            return None
        _y, _a, tile_obj = tile_res
        for ri in tile_obj.get("rowInfos", []):
            if int(ri.get("tileRowIndex", -1)) == row:
                return ri
        return None

    def set_cell_string(self, row: int, col: int, value: str) -> "Table":
        """Rewrite a STRING-typed cell. Raises ValueError if the cell
        is not already STRING-typed (we preserve cell record length to
        avoid corrupting downstream offsets)."""
        from kpa.tst_cells import set_cell_string
        ri = self._row_info_for(row)
        if ri is None:
            raise IndexError(f"row {row} not present in tile")
        st_res = self._strings_archive()
        if st_res is None:
            raise RuntimeError("table has no stringTable")
        st_yml, _st_arch, st_obj = st_res
        set_cell_string(ri, col, value, st_obj)
        # Mark every touched file dirty.
        deck = self._slide._deck
        tile_yml = self._tile_archive()[0]
        deck._mark_aux_dirty(tile_yml)
        deck._mark_aux_dirty(st_yml)
        self._slide._mark_dirty()
        return self

    def set_cell_int(self, row: int, col: int, value: int) -> "Table":
        """Rewrite an INT-typed cell. Raises ValueError if the cell is
        not already INT-typed."""
        from kpa.tst_cells import set_cell_int
        ri = self._row_info_for(row)
        if ri is None:
            raise IndexError(f"row {row} not present in tile")
        set_cell_int(ri, col, value)
        deck = self._slide._deck
        deck._mark_aux_dirty(self._tile_archive()[0])
        self._slide._mark_dirty()
        return self

    def set_cell_currency(self, row: int, col: int, value: int) -> "Table":
        """Rewrite a CURRENCY-typed cell (value is the raw u64). Raises
        ValueError if the cell is not already CURRENCY-typed."""
        from kpa.tst_cells import set_cell_currency
        ri = self._row_info_for(row)
        if ri is None:
            raise IndexError(f"row {row} not present in tile")
        set_cell_currency(ri, col, value)
        deck = self._slide._deck
        deck._mark_aux_dirty(self._tile_archive()[0])
        self._slide._mark_dirty()
        return self

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
