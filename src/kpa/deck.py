"""
kpa.deck — Deck object model
=============================

Step 4a + Step 4b. The ``Deck`` class is the entry point for both
template-anchored authoring and surgical editing of existing ``.key``
files.

Step 4a scope:
  - ``Deck.from_template(path)`` loads an existing .key into an internal
    representation that preserves the unpacked YAML tree verbatim.
  - ``Deck.save(path)`` writes the deck back to disk via keynote-parser's
    pack pipeline.
  - **F1 parity invariant:** ``Deck.from_template(svef).save(out)`` must
    produce a deck where round-tripping through unpack/repack/re-unpack
    yields the same per-file sha256 set as the source. This is the
    "no-op mutation" gate (S4.1).

Step 4b scope (new):
  - ``deck.slide[i]`` returns a :class:`kpa.objects.Slide` proxy.
  - ``slide.title``, ``slide.body``, ``slide.texts``, ``slide.images``.
  - Mutations write through into the loaded YAML tree, which is
    re-serialized on :meth:`save`.
  - F2b smoke: ``slide[i].title.set_text("New")``,
    ``slide[i].title.move(dy="20%")``, ``slide[i].body.set_position(...)``
    — saved deck opens cleanly in Keynote.app.

Internals:
  We wrap keynote-parser's existing ``File`` abstraction (which handles
  the IWA codec, ZIP packing, mapping). The KPA layer adds:
    - Pythonic indexing (``deck.slide[3]`` not ``deck.iwa_files["Index/Slide-X.iwa"]``)
    - Address book (``deck.slides.where(role="title")``)
    - Mutation API (Step 4b)
    - Brand validator (Step 4c)
"""

from __future__ import annotations

import builtins
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import yaml

_py_open = builtins.open  # avoid shadowing by module-level ``open`` below

from kpa.coords import DEFAULT_CANVAS
from kpa.objects import Slide, SlideList, _walk
from kpa.styles import Stylesheet, load_stylesheet


class Deck:
    """A Keynote presentation.

    Step 4a: load + save + summary.
    Step 4b: ``deck.slide[i]`` mutation surface.
    """

    def __init__(self, source_path: str | Path | None = None):
        """Create a Deck. Most users go through Deck.from_template() or kpa.open()."""
        self._source_path: Path | None = Path(source_path) if source_path else None
        self._workdir: Path | None = None
        self._owns_workdir: bool = False
        self._unpacked_root: Path | None = None
        # 4b internals
        self._slide_yaml_paths: list[Path] = []
        self._loaded_slides: dict[int, Slide] = {}
        self._dirty_slides: set[int] = set()
        self._canvas: tuple[float, float] = DEFAULT_CANVAS
        # 4c.1 internals
        self._stylesheet: Optional[Stylesheet] = None

    # --- construction --------------------------------------------------

    @classmethod
    def from_template(cls, path: str | Path) -> "Deck":
        """Load an existing ``.key`` file as a template for authoring/editing."""
        deck = cls(source_path=path)
        deck._load()
        return deck

    @classmethod
    def open(cls, path: str | Path) -> "Deck":
        """Module-level ``kpa.open(path)`` delegate."""
        deck = cls(source_path=path)
        deck._load()
        return deck

    # --- I/O -----------------------------------------------------------

    def _load(self):
        """Unpack the source ``.key`` into a working directory."""
        if self._source_path is None:
            raise ValueError("Deck has no source path; can't load.")
        if not self._source_path.exists():
            raise FileNotFoundError(self._source_path)

        from keynote_parser.codec import IWAFile  # noqa: F401  (verifies env)

        self._workdir = Path(tempfile.mkdtemp(prefix="kpa_deck_"))
        self._owns_workdir = True
        self._unpacked_root = self._workdir / "unpacked"

        result = subprocess.run(
            [
                "keynote-parser", "unpack",
                str(self._source_path),
                "--output", str(self._unpacked_root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"keynote-parser unpack failed for {self._source_path}:\n"
                f"  stderr: {result.stderr[-500:]}"
            )

        # Catalog slide YAML files in slide order. We need to read the
        # Document.iwa.yaml to find slide ordering. For Step 4b we use a
        # simpler approach: sort by file numeric id (which matches Keynote's
        # internal slide-creation order, generally NOT presentation order).
        # Step 5 will resolve real presentation order from KN.ShowArchive.
        idx_dir = self._unpacked_root / "Index"

        # Slide files are named ``Slide-<id>.iwa.yaml`` or, for slides
        # whose IWA payload spans multiple chunks, ``Slide-<id>-<n>.iwa.yaml``.
        # Apple also stores a single non-suffixed ``Slide.iwa.yaml`` for the
        # first slide in many decks (observed in SVEF, test1 — silently
        # dropped by the previous loader).
        #
        # Truth-of-record: a file is a slide-file iff it contains an object
        # whose ``_pbtype`` is ``KN.SlideArchive``. We scan the contents
        # rather than parsing filenames, then dedupe per SlideArchive id
        # (chunked files all describe the same slide).
        def _file_slide_id(p: Path) -> Optional[str]:
            """Return the KN.SlideArchive id contained in this file, or
            None if the file holds none. We avoid a full YAML parse
            (slow on large slide files) by sniffing the text first."""
            try:
                with _py_open(p) as fh:
                    text = fh.read()
            except Exception:
                return None
            if "_pbtype: KN.SlideArchive" not in text:
                return None
            # Walk via YAML to extract the id (must be exact).
            try:
                root = yaml.safe_load(text)
            except Exception:
                return None
            if not isinstance(root, dict):
                return None
            for chunk in root.get("chunks", []) or []:
                for arch in chunk.get("archives", []) or []:
                    for obj in arch.get("objects", []) or []:
                        if obj.get("_pbtype") == "KN.SlideArchive":
                            ident = arch.get("header", {}).get("identifier")
                            return str(ident) if ident is not None else None
            return None

        # Discover every file with a real KN.SlideArchive payload.
        candidate_files = sorted(idx_dir.glob("Slide*.iwa.yaml"))
        seen_slide_ids: set[str] = set()
        primary: list[Path] = []
        for p in candidate_files:
            sid = _file_slide_id(p)
            if sid is None or sid in seen_slide_ids:
                continue
            seen_slide_ids.add(sid)
            primary.append(p)

        # Sort by numeric slide id when possible (Keynote internal order;
        # presentation order resolves later via KN.ShowArchive in Step 5).
        def _sort_by_sid(p: Path):
            try:
                sid_int = int(_file_slide_id(p) or "0")
            except (ValueError, TypeError):
                sid_int = 0
            return (sid_int, p.name)
        primary.sort(key=_sort_by_sid)
        self._slide_yaml_paths = primary

        # Resolve canvas dimensions from Document.iwa.yaml's KN.ShowArchive.
        doc_path = idx_dir / "Document.iwa.yaml"
        if doc_path.exists():
            try:
                with _py_open(doc_path) as _fh:
                    doc = yaml.safe_load(_fh)
                for sub in _walk(doc):
                    if isinstance(sub, dict) and sub.get("_pbtype") == "KN.ShowArchive":
                        size = sub.get("size")
                        if (
                            isinstance(size, dict)
                            and "width" in size
                            and "height" in size
                        ):
                            self._canvas = (
                                float(size["width"]),
                                float(size["height"]),
                            )
                            break
            except yaml.YAMLError:
                pass  # fall back to DEFAULT_CANVAS

        # 4c.1: load the document stylesheet for style resolution
        self._stylesheet = load_stylesheet(self._unpacked_root)

    # ---------- Deck-wide cross-file archive index (4c.6.2-tables) ----------
    #
    # Some drawables a slide owns visually live in *other* Index files
    # rather than the slide's own YAML. The clearest case is on-slide
    # tables: ``TST.TableInfoArchive`` ships in
    # ``CalculationEngine.iwa.yaml`` even though its
    # ``super.parent.identifier`` points at the slide. The per-slide
    # ``_archive_index`` cannot reach those archives.
    #
    # This lazy index walks every ``Index/*.iwa.yaml`` once and indexes
    # every archive by its declared ``parent.identifier``. Slides query
    # it to find children that live in sibling files. Mutations on the
    # returned archive dicts mutate the cached YAML tree; ``save()``
    # already re-serializes any file whose path was touched.

    def _aux_yaml_root(self, yaml_path: Path) -> dict:
        """Lazy-load and cache an arbitrary Index/*.iwa.yaml file's parsed
        tree, so cross-file mutations flush on save()."""
        cache = getattr(self, "_aux_yaml_cache", None)
        if cache is None:
            cache = {}
            self._aux_yaml_cache = cache
        key = str(yaml_path)
        if key in cache:
            return cache[key]
        with _py_open(yaml_path) as fh:
            root = yaml.safe_load(fh)
        cache[key] = root
        return root

    def _mark_aux_dirty(self, yaml_path: Path) -> None:
        """Tell save() that this auxiliary file needs to be flushed."""
        dirty = getattr(self, "_aux_dirty", None)
        if dirty is None:
            dirty = set()
            self._aux_dirty = dirty
        dirty.add(str(yaml_path))

    # Cross-file pbtypes we index. Currently only on-slide tables; add
    # more as new sub-steps need them. The sniff filter keeps this fast
    # (a full text-scan per file is much cheaper than a YAML parse).
    _CROSS_FILE_PBTYPES = ("TST.TableInfoArchive",)

    def _by_parent_index(self) -> dict[str, list]:
        """Lazy: {parent_id -> [ (yaml_path, archive_dict, object_dict) ]}
        for archives in *other* Index files whose pbtype is in
        ``_CROSS_FILE_PBTYPES``. Skips slide-content files (those are
        already walked by ``Slide._archive_index``).

        Used by ``Slide.tables`` (and future cross-file lookups) to find
        drawables whose ``super.parent.identifier`` points back at a
        slide. Sniffs the raw text first to avoid YAML-parsing every
        file in large decks (SVEF has ~100 Index files; only one
        contains a TableInfoArchive).
        """
        cached = getattr(self, "_by_parent_cache", None)
        if cached is not None:
            return cached
        index: dict[str, list] = {}
        idx_dir = self._unpacked_root / "Index"
        slide_paths = {str(p) for p in self._slide_yaml_paths}
        for yml in idx_dir.rglob("*.iwa.yaml"):
            # Skip slide-content files: they're covered by per-slide indexes.
            if str(yml) in slide_paths:
                continue
            # Fast sniff: skip files that obviously don't carry any of the
            # cross-file pbtypes we care about. The file is read once for
            # the sniff; the YAML parse only happens on a hit.
            try:
                with _py_open(yml) as fh:
                    text = fh.read()
            except Exception:
                continue
            if not any(t in text for t in self._CROSS_FILE_PBTYPES):
                continue
            try:
                root = self._aux_yaml_root(yml)
            except Exception:
                continue
            if not isinstance(root, dict):
                continue
            for chunk in root.get("chunks", []) or []:
                for arch in chunk.get("archives", []) or []:
                    for obj in arch.get("objects", []) or []:
                        if obj.get("_pbtype") not in self._CROSS_FILE_PBTYPES:
                            continue
                        sup = obj.get("super")
                        if not isinstance(sup, dict):
                            continue
                        parent = sup.get("parent")
                        if not isinstance(parent, dict):
                            continue
                        pid = parent.get("identifier")
                        if pid is None:
                            continue
                        index.setdefault(str(pid), []).append((yml, arch, obj))
        self._by_parent_cache = index
        return index

    # ---------- Document.iwa lazy access (4c.5) ----------

    def _document_root(self) -> dict:
        """Load and cache the parsed Document.iwa.yaml tree (the deck-
        level archive: KN.ShowArchive, KN.Soundtrack, theme refs, etc.).

        Lazy: only read on first access; subsequent mutations live on
        ``self._document_yaml_root`` and are flushed on save().
        """
        if getattr(self, "_document_yaml_root", None) is not None:
            return self._document_yaml_root
        doc_path = self._unpacked_root / "Index" / "Document.iwa.yaml"
        with _py_open(doc_path) as fh:
            self._document_yaml_root = yaml.safe_load(fh)
        self._document_yaml_path = doc_path
        return self._document_yaml_root

    def _mark_document_dirty(self):
        """Tell save() the deck-level Document.iwa.yaml needs to be
        flushed back to disk."""
        self._document_dirty = True

    def _find_document_archive(self, pbtype: str) -> Optional[dict]:
        """Walk Document.iwa for the first archive matching a pbtype."""
        doc = self._document_root()
        for chunk in doc.get("chunks", []):
            for arch in chunk.get("archives", []):
                for obj in arch.get("objects", []):
                    if obj.get("_pbtype") == pbtype:
                        return obj
        return None

    def _find_document_archives(self, pbtype: str) -> list[dict]:
        """Walk Document.iwa for all archives matching a pbtype."""
        doc = self._document_root()
        out: list[dict] = []
        for chunk in doc.get("chunks", []):
            for arch in chunk.get("archives", []):
                for obj in arch.get("objects", []):
                    if obj.get("_pbtype") == pbtype:
                        out.append(obj)
        return out

    # ---------- soundtrack + live video (4c.5) ----------

    @property
    def soundtrack(self):
        """The deck-level :class:`Soundtrack` (one per deck). Returns
        ``None`` if the deck has no soundtrack archive (rare — Keynote
        creates one even when disabled)."""
        from kpa.media import Soundtrack
        arch = self._find_document_archive("KN.Soundtrack")
        if arch is None:
            return None
        return Soundtrack(deck=self, archive=arch)

    @property
    def live_video_sources(self) -> tuple:
        """All :class:`LiveVideoSource` entries (camera feed configs)."""
        from kpa.media import LiveVideoSource
        archs = self._find_document_archives("KN.LiveVideoSource")
        return tuple(LiveVideoSource(deck=self, archive=a) for a in archs)

    # ---------- 4c.8.2 new slide instantiation ----------

    def new_slide(self, *, kind: str, after=None):
        """Create a new slide from a template kind (4c.8.2).

        Parameters
        ----------
        kind : str
            Apple's canonical template name (case-insensitive), e.g.
            ``'BLANK'``, ``'TITLE_AND_BODY'``,
            ``'TITLE_AND_TWO_COLUMNS'``. See
            :func:`kpa.slide_kinds.list_slide_kinds` for the catalogue.
        after : int or None
            Insert position (0-based slide index). If None, the new
            slide is appended. ``after=0`` makes it the second slide.

        Returns
        -------
        Slide
            The newly created slide, fully mutable.
        """
        from kpa.new_slide import new_slide as _new_slide
        return _new_slide(self, kind=kind, after=after)

    def save(self, path: str | Path) -> Path:
        """Write the deck back to disk as a ``.key`` file.

        Step 4b: flushes any in-memory slide mutations to the unpacked
        YAML tree, then calls keynote-parser pack to re-zip.
        """
        if self._unpacked_root is None:
            raise RuntimeError("Deck has not been loaded; call from_template() first.")

        # Flush all dirty slides back to YAML on disk
        for i in sorted(self._dirty_slides):
            if i in self._loaded_slides:
                slide = self._loaded_slides[i]
                yaml_path = slide._yaml_path
                # keynote-parser default_flow_style + sort_keys settings:
                # we have to match the format keynote-parser emits so the
                # round-trip is sha256-stable when nothing's changed.
                with _py_open(yaml_path, "w") as f:
                    yaml.dump(
                        slide._yaml_root,
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
        self._dirty_slides.clear()

        # 4c.1: flush stylesheet if any style mutations were made
        if self._stylesheet is not None and self._stylesheet.is_dirty:
            self._stylesheet.flush()

        # 4c.5: flush Document.iwa.yaml if soundtrack/live-video edits
        if getattr(self, "_document_dirty", False) and getattr(
            self, "_document_yaml_root", None
        ) is not None:
            with _py_open(self._document_yaml_path, "w") as f:
                yaml.dump(
                    self._document_yaml_root,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
            self._document_dirty = False

        # 4c.6.2-tables: flush any auxiliary Index file (e.g. CalculationEngine.iwa.yaml)
        # whose cached YAML tree was mutated via the cross-file index.
        aux_dirty = getattr(self, "_aux_dirty", None)
        aux_cache = getattr(self, "_aux_yaml_cache", None)
        if aux_dirty and aux_cache:
            for key in list(aux_dirty):
                root = aux_cache.get(key)
                if root is None:
                    continue
                with _py_open(Path(key), "w") as f:
                    yaml.dump(
                        root,
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )
            self._aux_dirty = set()

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "keynote-parser", "pack",
                str(self._unpacked_root),
                "--output", str(out),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"keynote-parser pack failed for {self._unpacked_root}:\n"
                f"  stderr: {result.stderr[-500:]}"
            )
        return out

    # --- slide access (4b) --------------------------------------------

    @property
    def slide(self) -> SlideList:
        """Indexable view of slides: ``deck.slide[0]``, ``deck.slide[3]``."""
        return SlideList(self)

    @property
    def slides(self) -> SlideList:
        """Plural alias for ``deck.slide``."""
        return SlideList(self)

    @property
    def canvas(self) -> tuple[float, float]:
        """Slide canvas dimensions in points: (width, height)."""
        return self._canvas

    @property
    def stylesheet(self) -> Optional[Stylesheet]:
        """Document-level stylesheet (TSS.StylesheetArchive + every
        TSWP.* / TSD.* style archive). Used to resolve effective
        text/shape styles by ID."""
        return self._stylesheet

    def _load_slide(self, index: int) -> Slide:
        """Internal — load slide at ``index``, caching the parsed YAML root."""
        if index < 0:
            index += len(self._slide_yaml_paths)
        if not (0 <= index < len(self._slide_yaml_paths)):
            raise IndexError(
                f"Slide index {index} out of range; deck has "
                f"{len(self._slide_yaml_paths)} slides."
            )
        if index in self._loaded_slides:
            return self._loaded_slides[index]
        yaml_path = self._slide_yaml_paths[index]
        with _py_open(yaml_path) as f:
            root = yaml.safe_load(f)
        slide = Slide(
            deck=self,
            index=index,
            yaml_path=yaml_path,
            yaml_root=root,
            canvas=self._canvas,
        )
        self._loaded_slides[index] = slide
        # Once we expose a mutable proxy we have to assume the caller
        # might mutate it before save. Mark dirty pre-emptively. (This is
        # over-eager but safe: re-serializing an unchanged YAML through
        # PyYAML may not be byte-identical, so we don't dirty unless the
        # caller actually mutates.)
        # ... so we DON'T set dirty here. mark_dirty() is called by
        # mutator methods on Slide/TextBlock/Image.
        return slide

    def mark_dirty(self, index: int):
        """Internal — mark a slide as needing re-serialization on save."""
        self._dirty_slides.add(index)

    # --- summary -------------------------------------------------------

    def summary(self) -> str:
        if self._unpacked_root is None:
            return "<Deck: not loaded>"
        n_slides = len(self._slide_yaml_paths)
        n_data = (
            len(list((self._unpacked_root / "Data").iterdir()))
            if (self._unpacked_root / "Data").exists()
            else 0
        )
        return (
            f"<Deck: {self._source_path}\n"
            f"  slides: {n_slides}\n"
            f"  data assets: {n_data}\n"
            f"  canvas: {self._canvas[0]:.0f} x {self._canvas[1]:.0f} pt\n"
            f"  workdir: {self._unpacked_root}>"
        )

    def __repr__(self):
        return self.summary()

    # --- cleanup -------------------------------------------------------

    def close(self):
        if self._owns_workdir and self._workdir and self._workdir.exists():
            shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None
            self._unpacked_root = None
            self._slide_yaml_paths = []
            self._loaded_slides.clear()
            self._dirty_slides.clear()
            self._stylesheet = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(path: str | Path) -> Deck:  # noqa: A004 (intentional shadow at module level)
    """Open a ``.key`` file as a :class:`Deck`. Equivalent to :meth:`Deck.open`."""
    return Deck.open(path)
