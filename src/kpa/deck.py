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
        # We only want the primary file per slide id (the one without a
        # trailing ``-<n>`` chunk suffix).
        def _slide_sort_key(p: Path):
            stem = p.stem.replace(".iwa", "")
            parts = stem.split("-")
            # parts[0] == 'Slide'
            try:
                primary_id = int(parts[1])
            except (IndexError, ValueError):
                return (10**12, 0, stem)
            chunk_suffix = 0
            if len(parts) > 2:
                try:
                    chunk_suffix = int(parts[2])
                except ValueError:
                    chunk_suffix = 999
            return (primary_id, chunk_suffix, stem)

        all_slide_files = sorted(
            idx_dir.glob("Slide-*.iwa.yaml"),
            key=_slide_sort_key,
        )
        # Keep only the primary chunk per slide id.
        seen_ids: set[int] = set()
        primary: list[Path] = []
        for p in all_slide_files:
            stem = p.stem.replace(".iwa", "")
            parts = stem.split("-")
            try:
                pid = int(parts[1])
            except (IndexError, ValueError):
                continue
            if pid in seen_ids:
                continue
            if len(parts) == 2:  # primary chunk
                seen_ids.add(pid)
                primary.append(p)
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
