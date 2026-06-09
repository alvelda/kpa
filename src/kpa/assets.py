"""
kpa.assets
===========

Step 4c.8 second deliverable — asset grovel.

The ``Data/`` folder of an unpacked .key bundle holds every
embedded blob (images, movies, fonts, PDFs). Each file is
referenced by ``MediaData`` archives elsewhere in the deck. The
asset grovel API lets agents:

  * Enumerate all assets with size + kind classification
  * Extract one or all assets to a destination folder
  * Filter by kind (image / video / font / other)

The grovel is read-only on the deck — it copies blobs from the
unpacked workdir to a user-chosen folder.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:
    from kpa.deck import Deck


# Classification by extension. Conservative: anything not on this
# list is "other" so agents can decide what to do with it.
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".gif", ".webp",
              ".avif", ".heic", ".heif", ".bmp", ".svg"}
_VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
_AUDIO_EXT = {".m4a", ".mp3", ".aac", ".wav", ".aif", ".aiff", ".caf"}
_FONT_EXT = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}
_DOC_EXT = {".pdf"}


class Asset:
    """A single blob in the deck's ``Data/`` folder.

    Read-only; carries source path + lazy-computed metadata.
    """

    def __init__(self, source_path: Path):
        self._src = source_path

    @property
    def filename(self) -> str:
        return self._src.name

    @property
    def source_path(self) -> Path:
        """Path inside the deck's unpacked workdir (transient)."""
        return self._src

    @property
    def extension(self) -> str:
        return self._src.suffix.lower()

    @property
    def size_bytes(self) -> int:
        return self._src.stat().st_size

    @property
    def kind(self) -> str:
        """One of: 'image', 'video', 'audio', 'font', 'document', 'other'."""
        ext = self.extension
        if ext in _IMAGE_EXT:
            return "image"
        if ext in _VIDEO_EXT:
            return "video"
        if ext in _AUDIO_EXT:
            return "audio"
        if ext in _FONT_EXT:
            return "font"
        if ext in _DOC_EXT:
            return "document"
        return "other"

    def extract_to(self, dest_dir: Path | str) -> Path:
        """Copy this asset into ``dest_dir`` (must exist or will be
        created). Returns the destination path.
        """
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        out_path = dest / self.filename
        shutil.copy2(self._src, out_path)
        return out_path

    def __repr__(self) -> str:
        return f"<Asset {self.filename!r} kind={self.kind} size={self.size_bytes}>"


def list_assets(deck: "Deck", *, kind: Optional[str] = None) -> tuple[Asset, ...]:
    """Return every :class:`Asset` in the deck's ``Data/`` folder.

    Optional ``kind`` filter restricts to one of the classification
    buckets ('image' / 'video' / 'audio' / 'font' / 'document' /
    'other'). Filenames are deterministic-sorted.
    """
    if deck._unpacked_root is None:
        return tuple()
    data_dir = deck._unpacked_root / "Data"
    if not data_dir.is_dir():
        return tuple()
    out: list[Asset] = []
    for p in sorted(data_dir.iterdir()):
        if not p.is_file():
            continue
        a = Asset(p)
        if kind is None or a.kind == kind:
            out.append(a)
    return tuple(out)


def asset_summary(deck: "Deck") -> dict[str, dict]:
    """Aggregate asset stats by kind. Returns a dict:

    .. code-block:: python

        {
            "image":    {"count": 357, "bytes": 37103456},
            "video":    {"count": 2,   "bytes": 11772256},
            "document": {"count": 1,   "bytes":    15224},
            ...
            "total":    {"count": 436, "bytes": 53120000},
        }

    Useful for quick reports / sizing decisions before extraction.
    """
    out: dict[str, dict] = {}
    total_count = 0
    total_bytes = 0
    for a in list_assets(deck):
        bucket = out.setdefault(a.kind, {"count": 0, "bytes": 0})
        sz = a.size_bytes
        bucket["count"] += 1
        bucket["bytes"] += sz
        total_count += 1
        total_bytes += sz
    out["total"] = {"count": total_count, "bytes": total_bytes}
    return out


def extract_all_assets(deck: "Deck", dest_dir: Path | str, *,
                       kind: Optional[str] = None) -> list[Path]:
    """Copy every asset (optionally filtered by ``kind``) to
    ``dest_dir``. Returns the list of destination paths in the
    same deterministic order :func:`list_assets` returns.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for a in list_assets(deck, kind=kind):
        out.append(a.extract_to(dest))
    return out
