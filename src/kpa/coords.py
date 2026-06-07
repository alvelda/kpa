"""
kpa.coords — Coordinate semantics
==================================

Per Captain 2026-06-07 PRD v1.1: KPA accepts three coordinate
representations on every position/size argument:

  - **pct** (default): percentages of the slide canvas, 0..100.
    Most agent-friendly. ``"50%"`` = center of canvas (in that axis).
  - **pt**: IWA-native points. Direct mapping to Keynote's internal
    coordinate system. ``"349pt"`` = 349 points from the slide canvas
    top-left.
  - **px**: device pixels (96 DPI nominal). Useful when an agent has
    been thinking in pixel terms. ``"349px"`` = 349/96 inches = 261.75 pt.

Reference: canonical 16:9 SVEF / NCI deck canvas is 720 × 405 pt.

The internal storage is always IWA-native pt. All conversions land in
this module so the rest of KPA never has to think about units.

Usage:

    from kpa.coords import parse, to_pt

    parse("50%", axis="x", canvas=(720, 405))  -> 360.0  (pt)
    parse("50%", axis="y", canvas=(720, 405))  -> 202.5  (pt)
    parse("349pt", canvas=(720, 405))           -> 349.0  (pt)
    parse("96px", canvas=(720, 405))            -> 72.0   (pt; 96 px / 96 DPI * 72 pt/in)
    parse(349, canvas=(720, 405))               -> 349.0  (number defaults to pt for safety)
    parse(349.0, canvas=(720, 405), default_unit="pct", axis="x") -> 2514.6 (treated as pct)
"""

from __future__ import annotations

import re
from typing import Literal

Axis = Literal["x", "y"]
Unit = Literal["pct", "pt", "px"]

# 16:9 canonical canvas. Real values come from Document.iwa.yaml's
# ShowArchive.size on actual decks; we cache them per-deck.
DEFAULT_CANVAS = (720.0, 405.0)

# Convert 96 DPI px -> pt at 72 DPI.
PT_PER_PX = 72.0 / 96.0  # 0.75

_NUMBER_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(%|pct|pt|px)?\s*$")


def parse(
    value: str | int | float,
    *,
    axis: Axis | None = None,
    canvas: tuple[float, float] = DEFAULT_CANVAS,
    default_unit: Unit = "pt",
) -> float:
    """Parse a coordinate string/number into IWA-native points (float).

    Args:
        value: Either a number (treated as ``default_unit``) or a string
            like ``"50%"``, ``"349pt"``, ``"96px"``.
        axis: ``"x"`` or ``"y"`` — required when value is in percent
            (to know which canvas dimension to use). Pass ``None`` for
            sizes or for already-absolute units.
        canvas: ``(width_pt, height_pt)`` of the slide canvas. Defaults
            to 720 × 405.
        default_unit: Unit to assume for bare numbers. Default ``"pt"``
            because that's the IWA-native space; the canonical pct-default
            applies at the API layer (``TextBlock.set_position("50%", "50%")``
            still calls ``parse("50%", ...)``), not here.

    Returns:
        Float in IWA-native points (pt).

    Raises:
        ValueError: if the string can't be parsed or pct without axis.
    """
    if isinstance(value, (int, float)):
        unit = default_unit
        num = float(value)
    elif isinstance(value, str):
        m = _NUMBER_RE.match(value)
        if not m:
            raise ValueError(f"Can't parse coordinate value: {value!r}")
        num = float(m.group(1))
        unit_str = m.group(2)
        if unit_str is None:
            unit = default_unit
        elif unit_str in ("%", "pct"):
            unit = "pct"
        else:
            unit = unit_str  # type: ignore[assignment]
    else:
        raise TypeError(f"Coordinate must be str or number, got {type(value)}")

    if unit == "pt":
        return num
    if unit == "px":
        return num * PT_PER_PX
    if unit == "pct":
        if axis is None:
            raise ValueError(
                f"Percent coordinate {value!r} needs axis='x' or axis='y' to resolve."
            )
        dim = canvas[0] if axis == "x" else canvas[1]
        return num / 100.0 * dim

    raise ValueError(f"Unknown unit {unit!r}")  # unreachable


def to_pt(
    value: str | int | float,
    *,
    axis: Axis | None = None,
    canvas: tuple[float, float] = DEFAULT_CANVAS,
    default_unit: Unit = "pt",
) -> float:
    """Alias for :func:`parse` — emphasizes the conversion direction."""
    return parse(value, axis=axis, canvas=canvas, default_unit=default_unit)


def parse_delta(
    value: str | int | float,
    *,
    axis: Axis | None = None,
    canvas: tuple[float, float] = DEFAULT_CANVAS,
    default_unit: Unit = "pt",
) -> float:
    """Same as :func:`parse` but emphasizes that the value is a delta
    (for relative ``move(dx, dy)`` calls)."""
    return parse(value, axis=axis, canvas=canvas, default_unit=default_unit)
