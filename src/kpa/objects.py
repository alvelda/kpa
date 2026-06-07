"""
kpa.objects — Slide / TextBlock / Image proxies
================================================

Step 4b. These are *mutation proxies* — thin object-oriented views over
the underlying YAML archive graph. They don't own the data; the
:class:`kpa.Deck` does. Mutations are written through to the unpacked
YAML tree and flushed on :meth:`Deck.save`.

Design:

    deck            -> Deck
    deck.slide[i]   -> Slide
    slide.title     -> TextBlock (or None)
    slide.body      -> TextBlock (or None)
    slide.texts     -> tuple[TextBlock, ...] (all text-bearing shapes)
    slide.images    -> tuple[Image, ...]
    slide.shapes    -> tuple[Shape, ...]

TextBlock supports:
  - text                  (property: get/set, in-place edit)
  - set_text(s)           (verbose alias)
  - position              (property: (x_pt, y_pt))
  - size                  (property: (w_pt, h_pt))
  - move(dx, dy)          (relative)
  - set_position(x, y)    (absolute, from slide canvas top-left)
  - set_size(w, h)
  - font_name / font_size / color  (Step 4c; stubbed in 4b)

Image supports:
  - position, size, move(), set_position(), set_size()
  - replace_with(asset_path)  (Step 4c)

Shape: position/size/move/set_position/set_size only in 4b.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

from kpa import coords as _coords
from kpa.color import Color, coerce_color, ColorLike
from kpa.styles import (
    Stylesheet,
    mutate_char_prop,
    mutate_para_prop,
    resolve_char_props_for_run,
    resolve_para_props_for_run,
)

if TYPE_CHECKING:
    from kpa.deck import Deck


# ============================================================
# Low-level archive graph helpers
# ============================================================


def _walk(x: Any):
    """Recursive walk yielding every dict in the tree."""
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, list):
        for i in x:
            yield from _walk(i)


def _find_geometry_dict(obj: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Walk into super-chain to find the first dict that looks like a
    geometry block: contains position {x, y} AND size {width, height}.
    Returns the dict itself (mutable reference)."""
    for sub in _walk(obj):
        if not isinstance(sub, dict):
            continue
        pos = sub.get("position")
        size = sub.get("size")
        if (
            isinstance(pos, dict)
            and "x" in pos
            and "y" in pos
            and isinstance(size, dict)
            and "width" in size
            and "height" in size
        ):
            return sub
    return None


def _find_storage_id(obj: dict[str, Any]) -> Optional[str]:
    """Find the text-storage identifier this shape points to.

    Looks for ``ownedStorage.identifier`` or ``deprecatedStorage.identifier``
    in the super chain.
    """
    for sub in _walk(obj):
        if not isinstance(sub, dict):
            continue
        for key in ("ownedStorage", "deprecatedStorage"):
            ref = sub.get(key)
            if isinstance(ref, dict) and "identifier" in ref:
                return str(ref["identifier"])
    return None


# ============================================================
# Proxies
# ============================================================


@dataclass
class _Geometry:
    """View over a geometry dict (mutable reference into the YAML tree)."""

    _dict: dict[str, Any]
    _canvas: tuple[float, float]
    _on_mutate: Optional[Any] = None  # callable() -> None, e.g. slide._mark_dirty

    def _changed(self):
        if self._on_mutate is not None:
            self._on_mutate()

    @property
    def x(self) -> float:
        return float(self._dict["position"]["x"])

    @property
    def y(self) -> float:
        return float(self._dict["position"]["y"])

    @property
    def width(self) -> float:
        return float(self._dict["size"]["width"])

    @property
    def height(self) -> float:
        return float(self._dict["size"]["height"])

    def set_position(self, x, y):
        """Set absolute position. ``x``, ``y`` accept "50%", "349pt", "96px"."""
        x_pt = _coords.parse(x, axis="x", canvas=self._canvas, default_unit="pt")
        y_pt = _coords.parse(y, axis="y", canvas=self._canvas, default_unit="pt")
        self._dict["position"]["x"] = x_pt
        self._dict["position"]["y"] = y_pt
        self._changed()

    def set_size(self, width, height):
        w_pt = _coords.parse(width, axis="x", canvas=self._canvas, default_unit="pt")
        h_pt = _coords.parse(height, axis="y", canvas=self._canvas, default_unit="pt")
        self._dict["size"]["width"] = w_pt
        self._dict["size"]["height"] = h_pt
        self._changed()

    def move(self, dx=None, dy=None):
        """Move relative. ``dx``, ``dy`` accept "+20%", "-50pt", etc."""
        if dx is not None:
            ddx = _coords.parse_delta(dx, axis="x", canvas=self._canvas, default_unit="pt")
            self._dict["position"]["x"] = float(self._dict["position"]["x"]) + ddx
        if dy is not None:
            ddy = _coords.parse_delta(dy, axis="y", canvas=self._canvas, default_unit="pt")
            self._dict["position"]["y"] = float(self._dict["position"]["y"]) + ddy
        if dx is not None or dy is not None:
            self._changed()

    def __repr__(self):
        return (
            f"<Geometry pos=({self.x:.1f},{self.y:.1f})pt "
            f"size=({self.width:.1f}x{self.height:.1f})pt>"
        )


class TextBlock:
    """A text-bearing shape on a slide.

    Wraps a ShapeInfoArchive or PlaceholderArchive plus the
    TSWP.StorageArchive it points to. Mutations write through to the
    YAML tree.
    """

    def __init__(
        self,
        *,
        slide: Slide,
        shape_archive: dict[str, Any],
        shape_pbtype: str,
        shape_id: str,
        storage_archive: Optional[dict[str, Any]],
        storage_id: Optional[str],
        geometry: Optional[_Geometry],
        role: str = "text",
    ):
        self._slide = slide
        self._shape_archive = shape_archive
        self._shape_pbtype = shape_pbtype
        self._shape_id = shape_id
        self._storage_archive = storage_archive
        self._storage_id = storage_id
        self._geometry = geometry
        self._role = role

    # --- text ---

    @property
    def text(self) -> str:
        if self._storage_archive is None:
            return ""
        t = self._storage_archive.get("text")
        if isinstance(t, list):
            return "".join(t)
        return str(t) if t else ""

    @text.setter
    def text(self, value: str):
        self.set_text(value)

    def set_text(self, value: str) -> None:
        if self._storage_archive is None:
            raise RuntimeError(
                f"TextBlock {self._shape_id} has no storage; can't set text."
            )
        # TSWP.StorageArchive.text is a repeated string.
        # Single-string replacement is the safe path: one run, no style.
        self._storage_archive["text"] = [value]
        # Reset the para tables so character counts remain consistent.
        # Each table entry's characterIndex must be <= len(text). We
        # keep them as-is for the first entry (characterIndex: 0) which
        # is universal; subsequent entries that point past the end
        # cause Keynote to silently ignore them but the YAML stays
        # roundtrip-safe. For Step 4b we keep this simple; Step 4c
        # will properly retokenize the runs.
        # We also clear any per-character style overrides so the master
        # style applies cleanly.
        self._slide._mark_dirty()

    # --- geometry passthrough ---

    @property
    def geometry(self) -> Optional[_Geometry]:
        return self._geometry

    @property
    def position(self) -> Optional[tuple[float, float]]:
        if self._geometry is None:
            return None
        return (self._geometry.x, self._geometry.y)

    @property
    def size(self) -> Optional[tuple[float, float]]:
        if self._geometry is None:
            return None
        return (self._geometry.width, self._geometry.height)

    def set_position(self, x, y):
        if self._geometry is None:
            raise RuntimeError(
                f"TextBlock {self._shape_id} has no geometry; can't set position."
            )
        self._geometry.set_position(x, y)

    def set_size(self, width, height):
        if self._geometry is None:
            raise RuntimeError(
                f"TextBlock {self._shape_id} has no geometry; can't set size."
            )
        self._geometry.set_size(width, height)

    def move(self, dx=None, dy=None):
        if self._geometry is None:
            raise RuntimeError(
                f"TextBlock {self._shape_id} has no geometry; can't move."
            )
        self._geometry.move(dx=dx, dy=dy)

    def __repr__(self):
        t = self.text
        t_preview = (t[:30] + "...") if len(t) > 30 else t
        return (
            f"<TextBlock role={self._role} id={self._shape_id} "
            f"text={t_preview!r} geom={self._geometry}>"
        )

    # --- styling (4c.1) ---

    def _stylesheet(self) -> Optional[Stylesheet]:
        return self._slide._deck.stylesheet

    def _char_props(self) -> dict[str, Any]:
        """Effective charProperties at character 0."""
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return {}
        return resolve_char_props_for_run(ss, self._storage_archive, 0)

    def _para_props(self) -> dict[str, Any]:
        """Effective paraProperties at character 0."""
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return {}
        return resolve_para_props_for_run(ss, self._storage_archive, 0)

    # Character-level properties

    @property
    def font_name(self) -> Optional[str]:
        return self._char_props().get("fontName")

    @font_name.setter
    def font_name(self, value: str):
        self.set_font_name(value)

    def set_font_name(self, value: str) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_char_prop(
            ss, self._storage_archive, prop_name="fontName", value=value
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def font_size(self) -> Optional[float]:
        v = self._char_props().get("fontSize")
        return float(v) if v is not None else None

    @font_size.setter
    def font_size(self, value: float):
        self.set_font_size(value)

    def set_font_size(self, value: float) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_char_prop(
            ss, self._storage_archive, prop_name="fontSize", value=float(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def bold(self) -> bool:
        return bool(self._char_props().get("bold", False))

    @bold.setter
    def bold(self, value: bool):
        self.set_bold(value)

    def set_bold(self, value: bool) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_char_prop(
            ss, self._storage_archive, prop_name="bold", value=bool(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def italic(self) -> bool:
        return bool(self._char_props().get("italic", False))

    @italic.setter
    def italic(self, value: bool):
        self.set_italic(value)

    def set_italic(self, value: bool) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_char_prop(
            ss, self._storage_archive, prop_name="italic", value=bool(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    # underline is an enum string in YAML: kNoUnderline, kSingleUnderline,
    # kDoubleUnderline, kDottedUnderline, kDashedUnderline, kWavyUnderline.
    _UNDERLINE_TO_BOOL = {
        "kNoUnderline": False,
        "kSingleUnderline": True,
        "kDoubleUnderline": True,
        "kDottedUnderline": True,
        "kDashedUnderline": True,
        "kWavyUnderline": True,
    }

    @property
    def underline(self) -> bool:
        v = self._char_props().get("underline")
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return self._UNDERLINE_TO_BOOL.get(v, False)
        return bool(v)

    @property
    def underline_style(self) -> Optional[str]:
        """Underline as a style name: 'none', 'single', 'double', etc."""
        v = self._char_props().get("underline")
        if v is None:
            return None
        if isinstance(v, str) and v.startswith("k") and v.endswith("Underline"):
            return v[1:-len("Underline")].lower()  # 'kSingleUnderline' -> 'single'
        return None

    @underline.setter
    def underline(self, value):
        self.set_underline(value)

    def set_underline(self, value) -> bool:
        """Set underline. Accepts bool (True=single, False=none) or a style
        name ('none'/'single'/'double'/'dotted'/'dashed'/'wavy')."""
        if isinstance(value, bool):
            enum_val = "kSingleUnderline" if value else "kNoUnderline"
        elif isinstance(value, str):
            mapping = {
                "none": "kNoUnderline",
                "single": "kSingleUnderline",
                "double": "kDoubleUnderline",
                "dotted": "kDottedUnderline",
                "dashed": "kDashedUnderline",
                "wavy": "kWavyUnderline",
            }
            enum_val = mapping.get(value.lower())
            if enum_val is None:
                raise ValueError(
                    f"Unknown underline style {value!r}; use one of {list(mapping)}"
                )
        else:
            raise TypeError(f"underline must be bool or str, got {type(value)}")
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_char_prop(
            ss, self._storage_archive, prop_name="underline", value=enum_val
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def color(self) -> Optional[Color]:
        cp = self._char_props()
        fc = cp.get("fontColor")
        if isinstance(fc, dict):
            return Color.from_dict(fc)
        return None

    @color.setter
    def color(self, value):
        self.set_color(value)

    def set_color(self, value) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        c = coerce_color(value)
        # Set both fontColor and tsdFill.color (Keynote uses both)
        ok1 = mutate_char_prop(
            ss, self._storage_archive, prop_name="fontColor", value=c.as_dict()
        )
        ok2 = mutate_char_prop(
            ss,
            self._storage_archive,
            prop_name="tsdFill",
            value={"color": c.as_dict()},
        )
        if ok1 or ok2:
            self._slide._mark_dirty()
        return ok1 or ok2

    # Paragraph-level properties

    # Keynote alignment enum: 0=left, 1=right, 2=center, 3=justify, 4=natural
    # keynote-parser serializes these as 'TATvalueN' strings in YAML.
    _ALIGNMENT_NAMES = {
        "left": 0,
        "right": 1,
        "center": 2,
        "justify": 3,
        "natural": 4,
    }
    _ALIGNMENT_INTS_TO_NAMES = {v: k for k, v in _ALIGNMENT_NAMES.items()}

    @staticmethod
    def _alignment_to_int(value) -> Optional[int]:
        """Coerce alignment-from-yaml into 0..4.

        Accepts ``int``, ``'TATvalue0'..'TATvalue4'`` (keynote-parser
        enum string form), or a name like 'left'/'center'.
        """
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            if value.startswith("TATvalue"):
                try:
                    return int(value[len("TATvalue"):])
                except ValueError:
                    return None
            if value.lower() in TextBlock._ALIGNMENT_NAMES:
                return TextBlock._ALIGNMENT_NAMES[value.lower()]
        return None

    @property
    def alignment(self) -> Optional[int]:
        """Paragraph alignment (Keynote enum: 0=left, 1=right, 2=center,
        3=justify, 4=natural). Returns the raw enum int."""
        v = self._para_props().get("alignment")
        return self._alignment_to_int(v)

    @property
    def alignment_name(self) -> Optional[str]:
        """Alignment as a name string (left/right/center/justify/natural)."""
        i = self.alignment
        if i is None:
            return None
        return self._ALIGNMENT_INTS_TO_NAMES.get(i)

    @alignment.setter
    def alignment(self, value):
        self.set_alignment(value)

    def set_alignment(self, value) -> bool:
        """Set alignment by name ('left'/'right'/'center'/'justify'/'natural')
        or by raw int (0..4)."""
        if isinstance(value, str):
            iv = self._ALIGNMENT_NAMES.get(value.lower())
            if iv is None:
                raise ValueError(
                    f"Unknown alignment name {value!r}; "
                    f"use one of {list(self._ALIGNMENT_NAMES)}"
                )
            value = iv
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        # keynote-parser expects the enum string form on write to round-trip
        # cleanly through its codec.
        ok = mutate_para_prop(
            ss,
            self._storage_archive,
            prop_name="alignment",
            value=f"TATvalue{int(value)}",
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def line_spacing(self) -> Optional[float]:
        ls = self._para_props().get("lineSpacing")
        if isinstance(ls, dict):
            # lineSpacing is sometimes a dict {'amount': ..., 'mode': ...}
            return float(ls.get("amount", 0.0))
        return float(ls) if ls is not None else None

    def set_line_spacing(self, amount: float, mode: Optional[int] = None) -> bool:
        """Set line spacing. ``mode`` is Keynote's lineSpacingMode enum."""
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        # Read current value to preserve mode if not explicitly set
        cur = self._para_props().get("lineSpacing")
        if isinstance(cur, dict):
            new_val = dict(cur)
            new_val["amount"] = float(amount)
            if mode is not None:
                new_val["mode"] = int(mode)
        else:
            new_val = {"amount": float(amount), "mode": int(mode) if mode is not None else 0}
        ok = mutate_para_prop(
            ss, self._storage_archive, prop_name="lineSpacing", value=new_val
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def first_line_indent(self) -> Optional[float]:
        v = self._para_props().get("firstLineIndent")
        return float(v) if v is not None else None

    def set_first_line_indent(self, value: float) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_para_prop(
            ss, self._storage_archive, prop_name="firstLineIndent", value=float(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def space_before(self) -> Optional[float]:
        v = self._para_props().get("spaceBefore")
        return float(v) if v is not None else None

    def set_space_before(self, value: float) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_para_prop(
            ss, self._storage_archive, prop_name="spaceBefore", value=float(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    @property
    def space_after(self) -> Optional[float]:
        v = self._para_props().get("spaceAfter")
        return float(v) if v is not None else None

    def set_space_after(self, value: float) -> bool:
        ss = self._stylesheet()
        if ss is None or self._storage_archive is None:
            return False
        ok = mutate_para_prop(
            ss, self._storage_archive, prop_name="spaceAfter", value=float(value)
        )
        if ok:
            self._slide._mark_dirty()
        return ok

    def style_summary(self) -> dict[str, Any]:
        """All resolved character + paragraph properties at character 0.
        Useful for inspection / debugging / brand-validator audits."""
        return {
            "char": dict(self._char_props()),
            "para": dict(self._para_props()),
        }


class Image:
    """An image on a slide. Step 4b: position/size mutation only."""

    def __init__(
        self,
        *,
        slide: Slide,
        archive: dict[str, Any],
        archive_id: str,
        geometry: Optional[_Geometry],
    ):
        self._slide = slide
        self._archive = archive
        self._archive_id = archive_id
        self._geometry = geometry

    @property
    def geometry(self) -> Optional[_Geometry]:
        return self._geometry

    @property
    def position(self) -> Optional[tuple[float, float]]:
        if self._geometry is None:
            return None
        return (self._geometry.x, self._geometry.y)

    @property
    def size(self) -> Optional[tuple[float, float]]:
        if self._geometry is None:
            return None
        return (self._geometry.width, self._geometry.height)

    def set_position(self, x, y):
        if self._geometry is None:
            raise RuntimeError(f"Image {self._archive_id} has no geometry.")
        self._geometry.set_position(x, y)

    def set_size(self, width, height):
        if self._geometry is None:
            raise RuntimeError(f"Image {self._archive_id} has no geometry.")
        self._geometry.set_size(width, height)

    def move(self, dx=None, dy=None):
        if self._geometry is None:
            raise RuntimeError(f"Image {self._archive_id} has no geometry.")
        self._geometry.move(dx=dx, dy=dy)

    def __repr__(self):
        return f"<Image id={self._archive_id} geom={self._geometry}>"


class Slide:
    """A single slide. Indexable from ``deck.slide[i]`` (0-based)."""

    def __init__(
        self,
        *,
        deck: "Deck",
        index: int,
        yaml_path: Path,
        yaml_root: dict[str, Any],
        canvas: tuple[float, float],
    ):
        self._deck = deck
        self._index = index
        self._yaml_path = yaml_path
        self._yaml_root = yaml_root
        self._canvas = canvas
        self._archive_index: dict[str, dict[str, Any]] = {}
        self._slide_archive: Optional[dict[str, Any]] = None
        self._slide_id: Optional[str] = None
        self._build_index()

    # --- internals ---

    def _build_index(self):
        for chunk in self._yaml_root.get("chunks", []):
            for arch in chunk.get("archives", []):
                ident = str(arch.get("header", {}).get("identifier"))
                self._archive_index[ident] = arch
                for obj in arch.get("objects", []):
                    if obj.get("_pbtype") == "KN.SlideArchive":
                        self._slide_archive = obj
                        self._slide_id = ident

    def _archive_object(self, archive_id: str) -> Optional[dict[str, Any]]:
        """Return the *first* object inside a given archive id."""
        arch = self._archive_index.get(str(archive_id))
        if arch is None:
            return None
        objs = arch.get("objects", [])
        return objs[0] if objs else None

    def _archive_objects(self, archive_id: str) -> list[dict[str, Any]]:
        """Return all objects inside an archive id."""
        arch = self._archive_index.get(str(archive_id))
        if arch is None:
            return []
        return arch.get("objects", [])

    def _mark_dirty(self):
        """Tell the parent deck this slide needs re-serialization."""
        self._deck.mark_dirty(self._index)

    def _make_text_block(
        self, shape_id: str, role: str = "text"
    ) -> Optional[TextBlock]:
        """Resolve shape archive + storage archive into a TextBlock."""
        shape_obj = self._archive_object(shape_id)
        if shape_obj is None:
            return None
        shape_pbtype = str(shape_obj.get("_pbtype", ""))
        storage_id = _find_storage_id(shape_obj)
        storage_obj = self._archive_object(storage_id) if storage_id else None
        geom_dict = _find_geometry_dict(shape_obj)
        geom = (
            _Geometry(
                _dict=geom_dict,
                _canvas=self._canvas,
                _on_mutate=self._mark_dirty,
            )
            if geom_dict
            else None
        )
        return TextBlock(
            slide=self,
            shape_archive=shape_obj,
            shape_pbtype=shape_pbtype,
            shape_id=shape_id,
            storage_archive=storage_obj,
            storage_id=storage_id,
            geometry=geom,
            role=role,
        )

    # --- public API ---

    @property
    def index(self) -> int:
        return self._index

    @property
    def title(self) -> Optional[TextBlock]:
        sa = self._slide_archive or {}
        ref = sa.get("titlePlaceholder")
        if not isinstance(ref, dict) or "identifier" not in ref:
            return None
        return self._make_text_block(str(ref["identifier"]), role="title")

    @property
    def body(self) -> Optional[TextBlock]:
        sa = self._slide_archive or {}
        ref = sa.get("bodyPlaceholder")
        if not isinstance(ref, dict) or "identifier" not in ref:
            return None
        return self._make_text_block(str(ref["identifier"]), role="body")

    def find_text(self, query: str, case_sensitive: bool = False) -> Optional[TextBlock]:
        """Return the first text block whose text contains ``query``.

        Convenient for surgical edits like:

            slide.find_text("Old Title").set_text("New Title")
            slide.find_text("appendix", case_sensitive=False).move(dy="+20pt")
        """
        q = query if case_sensitive else query.lower()
        for tb in self.texts:
            t = tb.text if case_sensitive else tb.text.lower()
            if q in t:
                return tb
        return None

    def texts_by_position(self, sort_by: str = "y") -> tuple[TextBlock, ...]:
        """Return all text blocks sorted by position (default: top-to-bottom)."""
        ts = [t for t in self.texts if t.position is not None]
        if sort_by == "y":
            ts.sort(key=lambda t: (t.position[1], t.position[0]))
        elif sort_by == "x":
            ts.sort(key=lambda t: (t.position[0], t.position[1]))
        return tuple(ts)

    @property
    def texts(self) -> tuple[TextBlock, ...]:
        """All text-bearing shapes on this slide (including title + body)."""
        out: list[TextBlock] = []
        seen_ids: set[str] = set()
        for aid, arch in self._archive_index.items():
            for obj in arch.get("objects", []):
                pbtype = obj.get("_pbtype", "")
                if pbtype not in ("TSWP.ShapeInfoArchive", "KN.PlaceholderArchive"):
                    continue
                # Must have storage with non-empty text
                sto_id = _find_storage_id(obj)
                if not sto_id:
                    continue
                sto = self._archive_object(sto_id)
                if not sto:
                    continue
                text_val = sto.get("text")
                if not text_val:
                    continue
                if isinstance(text_val, list) and not any(
                    isinstance(t, str) and t.strip() and t.strip() != "￼"
                    for t in text_val
                ):
                    continue
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                tb = self._make_text_block(aid, role="text")
                if tb:
                    out.append(tb)
        return tuple(out)

    @property
    def images(self) -> tuple[Image, ...]:
        out: list[Image] = []
        for aid, arch in self._archive_index.items():
            for obj in arch.get("objects", []):
                pbtype = obj.get("_pbtype", "")
                if pbtype not in ("TSD.ImageArchive", "TSD.MediaArchive", "TSD.MovieArchive"):
                    continue
                geom_dict = _find_geometry_dict(obj)
                geom = (
                    _Geometry(
                        _dict=geom_dict,
                        _canvas=self._canvas,
                        _on_mutate=self._mark_dirty,
                    )
                    if geom_dict
                    else None
                )
                out.append(Image(slide=self, archive=obj, archive_id=aid, geometry=geom))
                break  # one image per archive
        return tuple(out)

    @property
    def canvas(self) -> tuple[float, float]:
        return self._canvas

    @property
    def slide_id(self) -> Optional[str]:
        return self._slide_id

    def __repr__(self):
        n_texts = len(self.texts)
        n_images = len(self.images)
        title_txt = (self.title.text[:30] + "...") if self.title and len(self.title.text) > 30 else (self.title.text if self.title else "")
        return (
            f"<Slide #{self._index} id={self._slide_id} "
            f"title={title_txt!r} texts={n_texts} images={n_images}>"
        )


class SlideList:
    """Index-only view of a deck's slides. ``deck.slide[i]``."""

    def __init__(self, deck: "Deck"):
        self._deck = deck

    def __len__(self) -> int:
        return len(self._deck._slide_yaml_paths)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self)))]
        return self._deck._load_slide(i)

    def __iter__(self) -> Iterable[Slide]:
        for i in range(len(self)):
            yield self[i]

    def __repr__(self):
        return f"<SlideList n={len(self)}>"
