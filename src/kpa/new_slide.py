"""
kpa.new_slide
==============

Step 4c.8.2 — `Deck.new_slide(kind=...)` template instantiation.

Creating a new slide in Keynote means:

1. Build a new ``KN.SlideArchive`` cloned from a template
   ``TemplateSlide-*.iwa.yaml``. Every identifier inside the clone
   (drawables, styles, placeholders, notes, guide storage) gets
   rewritten so it doesn't collide with the deck's existing ids.
2. Build a new ``KN.SlideNodeArchive`` wrapper that holds display
   metadata (depth, thumbnail cache info, etc.) and references the
   new SlideArchive. Its ``templateSlideId`` UUID pair is copied
   from an existing node that already uses the same template (when
   available) or synthesized.
3. Append ``{identifier: <new SlideNodeArchive id>}`` to the
   deck's ``KN.ShowArchive.slideTree.slides`` list.
4. Emit a new ``Slide-<id>.iwa.yaml`` file in ``Index/``.

The new slide is then accessible via ``deck.slide[-1]`` (or its
explicit index) and supports the full mutation surface
(``set_text``, ``move``, etc.) from 4b/4c.

This module exposes the orchestration helper :func:`new_slide`
which is wired onto :class:`kpa.Deck.new_slide` by ``deck.py``.

Engineering notes
-----------------
* ``TSP.ArchiveInfo.messageInfos`` for KN.SlideNodeArchive uses
  ``type: 4`` (observed in SVEF). For KN.SlideArchive it is ``type: 5``.
  The cloned SlideArchive already carries its own correct messageInfos
  from the template file — we don't rebuild it.
* The cloned SlideArchive's ``ownedDrawables`` / ``drawablesZOrder`` /
  placeholder fields all reference the rewritten local identifiers.
  External refs (stylesheet, theme, shared style ids) are preserved
  because they don't appear as ``header.identifier`` in the template
  file.
* Build siblings (KN.BuildArchive) are NOT cloned from the template
  on first-pass instantiation. None of the canonical Apple templates
  (BLANK / TITLE_AND_BODY / TITLE_AND_TWO_COLUMNS) ship with builds,
  so this is non-issue for those. A future iteration can clone+rewrite
  them when needed.
"""

from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

if TYPE_CHECKING:
    from kpa.deck import Deck
    from kpa.objects import Slide


# Message-type codes for TSP.ArchiveInfo.messageInfos. Verified from
# SVEF samples (see HANDOFF.md engineering finding #1).
_MSG_TYPE_SLIDE = 5         # KN.SlideArchive header
_MSG_TYPE_SLIDE_NODE = 4    # KN.SlideNodeArchive header (verified SVEF Document.iwa)


# =========== identifier allocation ===========


class _IdAllocator:
    """Hands out fresh identifiers that don't collide with any
    archive in the deck.

    Scans every YAML file in ``Index/`` once on first use, then
    just increments. New identifiers start at ``max + 1``.
    Allocator caches the deck-wide identifier set so a second
    call doesn't re-walk the disk.
    """

    def __init__(self, deck: "Deck"):
        self._deck = deck
        self._next: Optional[int] = None

    def _seed(self):
        # Reuse a cached high-water-mark on the deck instance so
        # subsequent new_slide() calls don't re-walk the disk. A single
        # text scan of every Index YAML for ``identifier: '<digits>'``
        # is dramatically faster than a full ``yaml.safe_load`` pass
        # (the largest file in SVEF is 2.3 MB / 75k lines of YAML).
        cached = getattr(self._deck, "_id_high_water_mark", None)
        if cached is not None:
            self._next = max(int(cached) + 1, 90_000_000)
            return
        max_id = 0
        idx = self._deck._unpacked_root / "Index"
        import re
        rx = re.compile(r"identifier:\s*'?(\d+)'?")
        for yp in idx.glob("*.iwa.yaml"):
            try:
                text = yp.read_text()
            except Exception:
                continue
            for m in rx.finditer(text):
                try:
                    v = int(m.group(1))
                except ValueError:
                    continue
                if v > max_id:
                    max_id = v
        # Bump well above max to avoid any chance of collision with
        # ids in chunks we haven't fully inspected.
        self._next = max(max_id + 1, 90_000_000)
        # Cache the high-water mark on the deck for subsequent
        # new_slide() calls in the same session. We bump it as we
        # consume ids; see next_id() below.
        self._deck._id_high_water_mark = self._next - 1

    def next_id(self) -> int:
        if self._next is None:
            self._seed()
        v = self._next
        self._next += 1
        # Keep the deck-level cache in sync so a follow-up new_slide()
        # call sees the right high-water mark.
        try:
            self._deck._id_high_water_mark = v
        except Exception:
            pass
        return v


# =========== clone with identifier rewriting ===========


def _collect_archive_identifiers(archive_chunks: list) -> set[str]:
    """Walk every archive header inside ``archive_chunks`` and
    collect the set of definition identifiers used as
    ``header.identifier`` on archives."""
    seen: set[str] = set()
    for chunk in archive_chunks:
        for arch in (chunk.get("archives") or []):
            hdr = arch.get("header") or {}
            ident = hdr.get("identifier")
            if ident is not None:
                seen.add(str(ident))
    return seen


def _build_id_map(definition_ids: set[str], allocator: _IdAllocator) -> dict[str, str]:
    """Map every old definition id to a fresh one."""
    out: dict[str, str] = {}
    for old in sorted(definition_ids, key=lambda s: int(s) if s.isdigit() else 0):
        out[old] = str(allocator.next_id())
    return out


def _rewrite_identifiers(node, id_map: dict[str, str]):
    """In-place walk: replace every ``identifier`` string value found
    in dicts (top-level or inside ``header`` / refs) using ``id_map``.

    Strings not in the map are left alone — they refer to objects
    OUTSIDE the cloned set (e.g. theme style ids, shared stylesheet
    archives), which we must NOT rewrite.

    Also rewrites ``objectReferences`` lists (these are object-ref
    arrays inside TSP.ArchiveInfo.messageInfos).
    """
    if isinstance(node, dict):
        # Direct identifier field
        if "identifier" in node and isinstance(node["identifier"], (str, int)):
            old = str(node["identifier"])
            if old in id_map:
                node["identifier"] = id_map[old]
        # objectReferences: list of id strings (raw)
        if "objectReferences" in node and isinstance(node["objectReferences"], list):
            node["objectReferences"] = [
                id_map.get(str(x), str(x)) for x in node["objectReferences"]
            ]
        for v in node.values():
            _rewrite_identifiers(v, id_map)
    elif isinstance(node, list):
        for x in node:
            _rewrite_identifiers(x, id_map)


def _clone_template_archives(
    template_yaml: dict,
    allocator: _IdAllocator,
) -> tuple[dict, str, dict[str, str]]:
    """Deep-copy a TemplateSlide YAML structure, rewrite all internal
    identifiers, and return ``(new_yaml_tree, new_slide_archive_id,
    id_map)``.

    Strips the ``name`` field on the cloned SlideArchive (templates
    have a canonical name; regular slides do not).
    """
    cloned = copy.deepcopy(template_yaml)
    chunks = cloned.get("chunks") or []
    definition_ids = _collect_archive_identifiers(chunks)
    id_map = _build_id_map(definition_ids, allocator)
    _rewrite_identifiers(cloned, id_map)

    # Find the new SlideArchive id + strip name
    slide_arch_id: Optional[str] = None
    for chunk in chunks:
        for arch in (chunk.get("archives") or []):
            hdr = arch.get("header") or {}
            objs = arch.get("objects") or []
            for obj in objs:
                if isinstance(obj, dict) and obj.get("_pbtype") == "KN.SlideArchive":
                    obj.pop("name", None)
                    slide_arch_id = str(hdr.get("identifier"))
    if slide_arch_id is None:
        raise RuntimeError("Cloned template has no KN.SlideArchive")
    return cloned, slide_arch_id, id_map


def _set_template_slide_ref(
    new_yaml: dict,
    template_identifier: str,
) -> None:
    """Set ``templateSlide.identifier = <template_identifier>`` on the
    cloned SlideArchive so the new slide knows which template it came
    from. Templates themselves don't carry a templateSlide field; only
    real slides do.
    """
    for chunk in (new_yaml.get("chunks") or []):
        for arch in (chunk.get("archives") or []):
            for obj in (arch.get("objects") or []):
                if isinstance(obj, dict) and obj.get("_pbtype") == "KN.SlideArchive":
                    obj["templateSlide"] = {"identifier": str(template_identifier)}
                    return


# =========== templateSlideId UUID synthesis ===========


def _synthesize_template_slide_uuid() -> dict:
    """Synthesize a fresh ``templateSlideId`` pair (two 64-bit
    unsigned integers as strings).

    Apple uses this pair as a thumbnail-cache key. New decks get a
    fresh pair; Keynote.app re-derives it from the templateSlide ref
    on next open if it ever cares about the value matching the
    theme's templates list. Synthesizing is safer than copying an
    existing slide's pair (which could collide with the thumbnail
    cache for the unrelated slide).
    """
    return {
        "lower": str(random.getrandbits(63)),
        "upper": str(random.getrandbits(63)),
    }


# =========== SlideNodeArchive construction ===========


def _build_slide_node_archive(
    slide_archive_id: str,
    template_uuid: dict,
    node_id: str,
) -> dict:
    """Build a fresh SlideNodeArchive wrapper for a new slide.

    Returns the wrapper dict in the same shape used by Document.iwa.
    """
    obj = {
        "_pbtype": "KN.SlideNodeArchive",
        "backgroundIsNoFillOrColorFillWithAlpha": True,
        "buildEventCount": 0,
        "buildEventCountCacheVersion": 2,
        "depth": 1,
        "hasBuilds": False,
        "hasExplicitBuilds": True,
        "hasExplicitBuildsCacheVersion": 2,
        "hasNote": False,
        "hasTransition": False,
        "isSkipped": False,
        "isSlideNumberVisible": True,
        "slide": {"identifier": slide_archive_id},
        "templateSlideId": {
            "lower": str(template_uuid["lower"]),
            "upper": str(template_uuid["upper"]),
        },
        "thumbnailsAreDirty": True,
    }
    wrapper = {
        "header": {
            "_pbtype": "TSP.ArchiveInfo",
            "identifier": str(node_id),
            "messageInfos": [
                {
                    "type": _MSG_TYPE_SLIDE_NODE,
                    "version": [1, 0, 5],
                    "objectReferences": [str(slide_archive_id)],
                }
            ],
        },
        "objects": [obj],
    }
    return wrapper


# =========== orchestration ===========


def new_slide(
    deck: "Deck",
    *,
    kind: str,
    after: Optional[int] = None,
) -> "Slide":
    """Create a new slide in ``deck`` from the template named ``kind``.

    Parameters
    ----------
    deck : Deck
        The deck to add the slide to.
    kind : str
        Canonical Apple template name (case-insensitive). Examples:
        ``'BLANK'``, ``'TITLE_AND_BODY'``, ``'TITLE_AND_TWO_COLUMNS'``.
        See :func:`kpa.slide_kinds.list_slide_kinds` for the full
        per-theme catalogue.
    after : int or None
        Insert position (0-based). If None, the new slide is appended
        at the end. ``after=0`` makes the new slide the second slide.

    Returns
    -------
    Slide
        The newly created slide, fully mutable.

    Raises
    ------
    ValueError
        If no template with the given ``kind`` exists in the deck's
        theme.
    """
    from kpa.slide_kinds import find_slide_kind

    if deck._unpacked_root is None:
        raise RuntimeError("Deck has not been loaded; call from_template() first.")

    sk = find_slide_kind(deck, name=kind)
    if sk is None:
        # try identifier
        sk = find_slide_kind(deck, identifier=kind)
    if sk is None:
        raise ValueError(
            f"No template slide named {kind!r} in this deck's theme. "
            f"Use kpa.slide_kinds.list_slide_kinds(deck) to enumerate."
        )

    # Load the template YAML in full so we have its archive chunks.
    tpl_yaml = yaml.safe_load(sk._yaml_path.read_text())
    allocator = _IdAllocator(deck)

    # Clone and rewrite identifiers
    new_yaml, slide_arch_id, _id_map = _clone_template_archives(tpl_yaml, allocator)

    # Wire the new slide back to its template so SlideKind discovery
    # (slide_kind_for_slide) round-trips.
    _set_template_slide_ref(new_yaml, sk.identifier)

    # Also include the template id in the SlideArchive's objectReferences
    # so the encoder serialises the reference correctly. We append rather
    # than replace because the cloned messageInfos already track local
    # ids; we only need to add the (external) template id once.
    _append_object_reference_to_slide_archive(new_yaml, sk.identifier)

    # templateSlideId UUID — synthesized; Apple's thumbnail cache keys
    # are derived per-slide so we don't need to copy from existing.
    uuid = _synthesize_template_slide_uuid()

    # Build SlideNodeArchive
    node_id = str(allocator.next_id())
    node_wrapper = _build_slide_node_archive(slide_arch_id, uuid, node_id)

    # Append SlideNodeArchive to Document.iwa.yaml's last chunk
    doc = deck._document_root()
    doc_chunks = doc.setdefault("chunks", [])
    if not doc_chunks:
        doc_chunks.append({"archives": []})
    doc_chunks[-1].setdefault("archives", []).append(node_wrapper)

    # Append to ShowArchive.slideTree.slides at the right position
    show = _find_show_archive(doc)
    if show is None:
        raise RuntimeError("Deck has no KN.ShowArchive; cannot register slide.")
    slide_tree = show.setdefault("slideTree", {})
    slides_list = slide_tree.setdefault("slides", [])
    new_ref = {"identifier": node_id}
    if after is None:
        slides_list.append(new_ref)
    else:
        # after is index of the existing slide; new slide goes after it
        insert_at = int(after) + 1
        slides_list.insert(insert_at, new_ref)

    deck._mark_document_dirty()

    # Write the new slide YAML file
    new_yaml_path = deck._unpacked_root / "Index" / f"Slide-{slide_arch_id}.iwa.yaml"
    with open(new_yaml_path, "w") as f:
        yaml.dump(new_yaml, f, default_flow_style=False, sort_keys=False,
                  allow_unicode=True)

    # Register in deck's catalog at the right position
    if after is None:
        deck._slide_yaml_paths.append(new_yaml_path)
        new_index = len(deck._slide_yaml_paths) - 1
    else:
        insert_at = int(after) + 1
        deck._slide_yaml_paths.insert(insert_at, new_yaml_path)
        new_index = insert_at
        # Invalidate cached slides at and after the insertion point —
        # their positional indices shifted.
        old_loaded = dict(deck._loaded_slides)
        old_dirty = set(deck._dirty_slides)
        deck._loaded_slides.clear()
        deck._dirty_slides.clear()
        for old_idx, s in old_loaded.items():
            new_idx = old_idx if old_idx < insert_at else old_idx + 1
            s._index = new_idx  # keep proxy's view of its own index correct
            deck._loaded_slides[new_idx] = s
        for old_idx in old_dirty:
            new_idx = old_idx if old_idx < insert_at else old_idx + 1
            deck._dirty_slides.add(new_idx)

    # Eagerly load the new slide so caller can mutate it
    return deck.slide[new_index]


def _append_object_reference_to_slide_archive(
    new_yaml: dict,
    extra_id: str,
) -> None:
    """Append ``extra_id`` to the SlideArchive's TSP.ArchiveInfo
    ``messageInfos[0].objectReferences`` list if it isn't already there.
    This is needed so that fields like ``templateSlide.identifier``
    that we set after cloning are tracked by the encoder.
    """
    for chunk in (new_yaml.get("chunks") or []):
        for arch in (chunk.get("archives") or []):
            objs = arch.get("objects") or []
            if not any(
                isinstance(o, dict) and o.get("_pbtype") == "KN.SlideArchive"
                for o in objs
            ):
                continue
            hdr = arch.get("header") or {}
            mis = hdr.get("messageInfos") or []
            if not mis:
                continue
            refs = mis[0].setdefault("objectReferences", [])
            if str(extra_id) not in [str(x) for x in refs]:
                refs.append(str(extra_id))
            return


def _find_show_archive(doc_yaml: dict) -> Optional[dict]:
    """Walk Document.iwa.yaml and return the KN.ShowArchive dict."""
    def walk(n):
        if isinstance(n, dict):
            if n.get("_pbtype") == "KN.ShowArchive":
                return n
            for v in n.values():
                r = walk(v)
                if r is not None:
                    return r
        elif isinstance(n, list):
            for x in n:
                r = walk(x)
                if r is not None:
                    return r
        return None
    return walk(doc_yaml)
