"""
kpa.deck — Deck object model
=============================

Step 4a foundation. The ``Deck`` class is the entry point for both
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

Step 4b adds mutation methods (``slide[i].title.move(...)`` etc.)
Step 4c adds brand-compliance validation.
Step 4d adds the CLI DSL.

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
import tempfile
from pathlib import Path
from typing import Any

# We import keynote_parser lazily because protobuf import is heavy
# and we want the package to import quickly even when only metadata is
# needed.


class Deck:
    """A Keynote presentation.

    Step 4a: load + save + summary only. Mutation API lands in Step 4b.

    Use cases:

      >>> # Load existing deck for inspection
      >>> deck = kpa.open("path/to/deck.key")
      >>> print(deck.summary())

      >>> # Load existing deck as template for new authoring
      >>> deck = kpa.Deck.from_template("path/to/template.key")
      >>> # ... mutations in Step 4b ...
      >>> deck.save("path/to/output.key")
    """

    def __init__(self, source_path: str | Path | None = None):
        """Create a Deck. Most users go through Deck.from_template() or kpa.open()."""
        self._source_path: Path | None = Path(source_path) if source_path else None
        self._workdir: Path | None = None  # set by _load
        self._owns_workdir: bool = False  # if True, cleanup on close
        self._unpacked_root: Path | None = None  # path to unpacked tree

    # --- construction --------------------------------------------------

    @classmethod
    def from_template(cls, path: str | Path) -> Deck:
        """Load an existing ``.key`` file as a template for authoring/editing.

        This is the canonical Step 4a entry point. Equivalent to ``kpa.open(path)``
        for now; Step 4b distinguishes the two by behavior (``from_template``
        also exposes the template's slide kinds as cloning sources).
        """
        deck = cls(source_path=path)
        deck._load()
        return deck

    @classmethod
    def open(cls, path: str | Path) -> Deck:
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

        # Use keynote-parser's unpack pipeline so we inherit all of our
        # patches (Bug #1-#5) without re-implementing.
        from keynote_parser.codec import IWAFile  # noqa: F401  (verifies env)
        from keynote_parser.file_utils import process

        self._workdir = Path(tempfile.mkdtemp(prefix="kpa_deck_"))
        self._owns_workdir = True
        self._unpacked_root = self._workdir / "unpacked"

        # process(input, output_dir, mode='unpack') from keynote-parser
        # — we shell out to the CLI for now because the public Python API
        # is thin. Step 4b: import the function directly for speed.
        import subprocess
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

    def save(self, path: str | Path) -> Path:
        """Write the deck back to disk as a ``.key`` file.

        Step 4a: pure round-trip (no mutations applied). F1 parity is
        the test invariant.
        """
        if self._unpacked_root is None:
            raise RuntimeError("Deck has not been loaded; call from_template() first.")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
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

    # --- summary -------------------------------------------------------

    def summary(self) -> str:
        """Human-readable text summary of the deck."""
        if self._unpacked_root is None:
            return "<Deck: not loaded>"
        idx = self._unpacked_root / "Index"
        n_slides = len(list(idx.glob("Slide-*.iwa.yaml"))) if idx.exists() else 0
        n_data = (
            len(list((self._unpacked_root / "Data").iterdir()))
            if (self._unpacked_root / "Data").exists()
            else 0
        )
        return (
            f"<Deck: {self._source_path}\n"
            f"  slides: {n_slides}\n"
            f"  data assets: {n_data}\n"
            f"  workdir: {self._unpacked_root}>"
        )

    def __repr__(self):
        return self.summary()

    # --- cleanup -------------------------------------------------------

    def close(self):
        """Remove the working directory. Optional; gc will do this too."""
        if self._owns_workdir and self._workdir and self._workdir.exists():
            shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None
            self._unpacked_root = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def open(path: str | Path) -> Deck:  # noqa: A004 (intentional shadow at module level)
    """Open a ``.key`` file as a :class:`Deck`.

    Equivalent to :meth:`Deck.open`.
    """
    return Deck.open(path)
