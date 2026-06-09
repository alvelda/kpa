"""
kpa.slide_kinds
================

Step 4c.8 first deliverable — slide-kind library.

Apple ships every Keynote theme with a set of canonical template
slides (KN.SlideArchive instances in ``TemplateSlide-*.iwa.yaml``).
Each carries a ``name`` field with Apple's canonical kind name:

  * ``BLANK``
  * ``TITLE_AND_BODY``
  * ``TITLE_AND_TWO_COLUMNS``
  * ``Content No Text``
  * ``Blank Page_Image``
  * ``1_Blank Page_Image``
  * ... and theme-specific variants

The :class:`SlideKind` proxy wraps one such template, exposing its
name + identifier + canonical placeholder layout for discovery. The
:func:`list_slide_kinds` accessor returns every template in the
deck's theme — agents pick a kind by name and use it as the basis
for new slides (full ``new_slide(kind=...)`` deferred to 4c.8.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from kpa.escape import RawArchiveMixin

if TYPE_CHECKING:
    from kpa.deck import Deck


class SlideKind(RawArchiveMixin):
    """Read-only proxy over a single template slide.

    Each :class:`SlideKind` wraps a :class:`KN.SlideArchive` that
    lives in a ``TemplateSlide-*.iwa.yaml`` file. Its ``name`` field
    is the canonical kind identifier (e.g. ``"TITLE_AND_BODY"``).
    """

    def __init__(self, *, deck: "Deck", archive: dict[str, Any], identifier: str,
                 yaml_path):
        self._deck = deck
        self._archive = archive
        self._identifier = str(identifier)
        self._yaml_path = yaml_path

    # ---- RawArchiveMixin hooks ----

    def _raw_archive_root(self) -> dict:
        return self._archive

    def _raw_mark_dirty(self) -> None:
        # Template slide mutation marks the deck dirty by the same
        # mechanism the regular slides use — they live in the same
        # IWA YAML structure. For 4c.8 first pass we are read-only,
        # so this hook is a placeholder for 4c.8.2 writes.
        pass

    # ---- metadata ----

    @property
    def identifier(self) -> str:
        """The template's archive identifier (e.g. ``'652'``)."""
        return self._identifier

    @property
    def name(self) -> Optional[str]:
        """Apple's canonical kind name, e.g. ``'TITLE_AND_BODY'`` or
        ``'BLANK'`` or theme-author labels like ``'Content No Text'``.
        """
        return self._archive.get("name")

    @property
    def yaml_filename(self) -> str:
        return self._yaml_path.name

    # ---- placeholder layout (discovery for agents) ----

    @property
    def has_title_placeholder(self) -> bool:
        tp = self._archive.get("titlePlaceholder")
        return isinstance(tp, dict) and len(tp) > 0

    @property
    def has_body_placeholder(self) -> bool:
        bp = self._archive.get("bodyPlaceholder")
        return isinstance(bp, dict) and len(bp) > 0

    @property
    def has_object_placeholder(self) -> bool:
        op = self._archive.get("objectPlaceholder")
        return isinstance(op, dict) and len(op) > 0

    @property
    def has_slide_number_placeholder(self) -> bool:
        sp = self._archive.get("slideNumberPlaceholder")
        return isinstance(sp, dict) and len(sp) > 0

    @property
    def drawable_count(self) -> int:
        """Number of items in the template's ``ownedDrawables`` list."""
        d = self._archive.get("ownedDrawables")
        return len(d) if isinstance(d, list) else 0

    def __repr__(self) -> str:
        n = self.name or "(unnamed)"
        return f"<SlideKind #{self._identifier} name={n!r}>"


# =========== deck-level accessors ===========


def list_slide_kinds(deck: "Deck") -> tuple[SlideKind, ...]:
    """Return every template slide registered in the deck's theme.

    Iterates ``KN.ThemeArchive.templates`` for the canonical list,
    then resolves each identifier to its TemplateSlide YAML file.
    Empty tuple if the theme has no templates (theme-less decks
    should not exist in practice, but the API tolerates it).
    """
    out: list[SlideKind] = []
    # Walk every TemplateSlide-*.iwa.yaml in the unpacked Index/
    if deck._unpacked_root is None:
        return tuple()
    idx_dir = deck._unpacked_root / "Index"
    for ypath in sorted(idx_dir.glob("TemplateSlide-*.iwa.yaml")):
        try:
            from yaml import safe_load
            data = safe_load(ypath.read_text())
        except Exception:
            continue
        # Find KN.SlideArchive in the template file
        ident, arch = _find_template_archive(data)
        if arch is None:
            continue
        out.append(SlideKind(deck=deck, archive=arch, identifier=ident, yaml_path=ypath))
    return tuple(out)


def find_slide_kind(deck: "Deck", *, name: Optional[str] = None,
                    identifier: Optional[str | int] = None) -> Optional[SlideKind]:
    """Return the first :class:`SlideKind` matching the given name
    or identifier. Name match is case-insensitive on Apple's
    canonical names; identifier is exact (string-compared).
    """
    if name is None and identifier is None:
        return None
    needle_name = name.upper() if name is not None else None
    needle_id = str(identifier) if identifier is not None else None
    for sk in list_slide_kinds(deck):
        if needle_id is not None and sk.identifier == needle_id:
            return sk
        if needle_name is not None and (sk.name or "").upper() == needle_name:
            return sk
    return None


def slide_kind_for_slide(slide) -> Optional[SlideKind]:
    """Return the :class:`SlideKind` that a given :class:`Slide`
    references via its ``templateSlide`` pointer, or None.
    """
    sa = slide._slide_archive
    if sa is None:
        return None
    ts = sa.get("templateSlide")
    if not isinstance(ts, dict):
        return None
    ident = ts.get("identifier")
    if ident is None:
        return None
    return find_slide_kind(slide._deck, identifier=ident)


# ---- helpers ----


def _find_template_archive(data) -> tuple[Optional[str], Optional[dict]]:
    """Walk a TemplateSlide YAML and return (identifier, KN.SlideArchive)."""
    # Structure: { chunks: [ { archives: [ { header: {identifier}, objects: [{...KN.SlideArchive}] } ] } ] }
    for chunk in (data.get("chunks") or []):
        for arch in (chunk.get("archives") or []):
            ident = str((arch.get("header") or {}).get("identifier", "")) or None
            for obj in (arch.get("objects") or []):
                if isinstance(obj, dict) and obj.get("_pbtype") == "KN.SlideArchive":
                    return ident, obj
    return None, None
