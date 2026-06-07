"""
kpa.color — Color value type
=============================

Keynote stores colors as RGBA dicts inside archives:

    {
      "model": "rgb",
      "rgbspace": "srgb",
      "r": 0.952,  # 0.0–1.0
      "g": 0.443,
      "b": 0.0,
      "a": 1.0,
    }

The :class:`Color` class normalizes that representation and gives
agents a comfortable API:

    >>> Color(1.0, 0.443, 0.0)                    # rgb 0–1
    >>> Color.from_rgb255(243, 113, 0)
    >>> Color.from_hex("#F37100")
    >>> color.as_hex()           # "#F37100"
    >>> color.as_dict()          # the IWA archive dict

Alpha defaults to 1.0 (opaque).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


@dataclass(frozen=True)
class Color:
    """Immutable RGBA color (each channel 0.0–1.0)."""

    r: float
    g: float
    b: float
    a: float = 1.0

    def __post_init__(self):
        for ch_name, ch_val in (("r", self.r), ("g", self.g), ("b", self.b), ("a", self.a)):
            if not (0.0 - 1e-6 <= ch_val <= 1.0 + 1e-6):
                raise ValueError(
                    f"Color channel {ch_name}={ch_val} out of range [0, 1]"
                )

    # --- constructors ---

    @classmethod
    def from_rgb255(cls, r: int, g: int, b: int, a: int = 255) -> "Color":
        """From 0–255 integers."""
        return cls(r / 255.0, g / 255.0, b / 255.0, a / 255.0)

    @classmethod
    def from_hex(cls, hex_str: str) -> "Color":
        """From ``#RRGGBB`` or ``#RRGGBBAA``."""
        m = _HEX_RE.match(hex_str.strip())
        if not m:
            raise ValueError(f"Bad hex color: {hex_str!r}")
        h = m.group(1)
        if len(h) == 6:
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
            return cls(r, g, b, 1.0)
        # 8 hex chars
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        a = int(h[6:8], 16) / 255.0
        return cls(r, g, b, a)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Color":
        """From the IWA archive RGBA dict."""
        return cls(
            r=float(d.get("r", 0.0)),
            g=float(d.get("g", 0.0)),
            b=float(d.get("b", 0.0)),
            a=float(d.get("a", 1.0)),
        )

    # --- emitters ---

    def as_dict(self) -> dict[str, Any]:
        """Emit the IWA archive RGBA dict."""
        return {
            "a": float(self.a),
            "b": float(self.b),
            "g": float(self.g),
            "model": "rgb",
            "r": float(self.r),
            "rgbspace": "srgb",
        }

    def as_hex(self) -> str:
        """Emit ``#RRGGBB`` (ignores alpha)."""
        return "#{:02X}{:02X}{:02X}".format(
            int(round(self.r * 255)),
            int(round(self.g * 255)),
            int(round(self.b * 255)),
        )

    def as_hex_rgba(self) -> str:
        """Emit ``#RRGGBBAA``."""
        return "#{:02X}{:02X}{:02X}{:02X}".format(
            int(round(self.r * 255)),
            int(round(self.g * 255)),
            int(round(self.b * 255)),
            int(round(self.a * 255)),
        )

    def __repr__(self):
        return f"Color({self.as_hex()}, a={self.a:.2f})"


# --- coercion helper ---

ColorLike = Color | str | tuple[float, float, float] | tuple[float, float, float, float] | dict[str, Any]


def coerce_color(value: ColorLike) -> Color:
    """Convert anything color-shaped into a :class:`Color`.

    Accepts:
      - :class:`Color`
      - "#RRGGBB" / "#RRGGBBAA"
      - (r, g, b) tuple of 0–1 floats
      - (r, g, b, a) tuple of 0–1 floats
      - IWA RGBA dict
    """
    if isinstance(value, Color):
        return value
    if isinstance(value, str):
        return Color.from_hex(value)
    if isinstance(value, dict):
        return Color.from_dict(value)
    if isinstance(value, tuple):
        if len(value) == 3:
            return Color(*value)
        if len(value) == 4:
            return Color(*value)
    raise TypeError(f"Can't coerce {type(value).__name__} to Color: {value!r}")
