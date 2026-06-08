"""
kpa.media — Movie + Soundtrack + LiveVideoSource proxies (Step 4c.5)
=====================================================================

Schema notes (observed in SVEF + NCI samples):

  **TSD.MovieArchive** (embedded video/audio clip):
    audioOnly: bool           (treat as audio-only)
    startTime: float          (trim start, seconds)
    endTime: float            (trim end, seconds)
    posterTime: float         (thumbnail frame timestamp)
    volume: float             (0.0 - 1.0)
    loopOption: str           ("None" / "Repeat" / "BackAndForth")
    playsAcrossSlides: bool
    streaming: bool
    naturalSize: {width, height}
    originalSize: {width, height}
    movieData.identifier: str       (ref to embedded media blob)
    posterImageData.identifier: str (ref to poster image blob)
    style.identifier: str           (ref to TSD.MediaStyleArchive)
    super: {geometry, parent, locked, title, caption, ...}   (TSD base)

  **KN.Soundtrack** (deck-level audio track, lives in Document.iwa):
    mode: str         ("kKNSoundtrackModePlayOnce" / Off / Loop)
    volume: float

  **KN.LiveVideoSource** (camera feed config):
    name: str
    isDefaultSource: bool
    symbolImageIdentifier: int
    symbolTintColorIdentifier: int

The wrapper archive's TSP.ArchiveInfo messageInfos.type for
TSD.MovieArchive is **3007** (observed empirically). For
KN.Soundtrack the type is **N/A** (lives only in Document.iwa,
no add-from-scratch path needed in 4c.5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from kpa.escape import RawArchiveMixin

if TYPE_CHECKING:
    from kpa.objects import Slide


# ============================================================
# Constants
# ============================================================

LOOP_NONE = "None"
LOOP_REPEAT = "Repeat"
LOOP_BACK_AND_FORTH = "BackAndForth"

# Convenience aliases for callers
LOOP_ALIASES = {
    "off": LOOP_NONE,
    "no": LOOP_NONE,
    "false": LOOP_NONE,
    "once": LOOP_NONE,
    "none": LOOP_NONE,
    "loop": LOOP_REPEAT,
    "repeat": LOOP_REPEAT,
    "yes": LOOP_REPEAT,
    "true": LOOP_REPEAT,
    "pingpong": LOOP_BACK_AND_FORTH,
    "ping-pong": LOOP_BACK_AND_FORTH,
    "back_and_forth": LOOP_BACK_AND_FORTH,
    "backandforth": LOOP_BACK_AND_FORTH,
    "bounce": LOOP_BACK_AND_FORTH,
}

SOUNDTRACK_PLAY_ONCE = "kKNSoundtrackModePlayOnce"
SOUNDTRACK_LOOP = "kKNSoundtrackModeLoop"
SOUNDTRACK_OFF = "kKNSoundtrackModeOff"

SOUNDTRACK_MODE_ALIASES = {
    "once": SOUNDTRACK_PLAY_ONCE,
    "play_once": SOUNDTRACK_PLAY_ONCE,
    "playonce": SOUNDTRACK_PLAY_ONCE,
    "loop": SOUNDTRACK_LOOP,
    "repeat": SOUNDTRACK_LOOP,
    "off": SOUNDTRACK_OFF,
    "none": SOUNDTRACK_OFF,
    "disabled": SOUNDTRACK_OFF,
}


def resolve_loop(value: str) -> str:
    """Translate alias ('off', 'loop', 'pingpong') into the Keynote
    enum string. Unknown values pass through unchanged (so already-
    correct strings like 'Repeat' still work)."""
    return LOOP_ALIASES.get(value.lower(), value)


def resolve_soundtrack_mode(value: str) -> str:
    return SOUNDTRACK_MODE_ALIASES.get(value.lower(), value)


# ============================================================
# Movie proxy
# ============================================================


class Movie(RawArchiveMixin):
    """Wraps a single :class:`TSD.MovieArchive`.

    Exposes read+write access to all the movie-specific properties.
    Geometry (position/size/angle) is intentionally NOT duplicated here;
    use ``slide.images`` to get the matching :class:`Image` proxy for
    geometry mutation (the Image API already handles MovieArchive
    geometry via the common ``super.geometry`` path).
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

    @property
    def archive_id(self) -> str:
        return self._archive_id

    @property
    def is_audio_only(self) -> bool:
        return bool(self._archive.get("audioOnly", False))

    @is_audio_only.setter
    def is_audio_only(self, value: bool):
        self.set_audio_only(value)

    def set_audio_only(self, value: bool) -> "Movie":
        self._archive["audioOnly"] = bool(value)
        self._slide._mark_dirty()
        return self

    # ---- timing ----

    @property
    def start_time(self) -> Optional[float]:
        v = self._archive.get("startTime")
        return float(v) if v is not None else None

    @start_time.setter
    def start_time(self, value: float):
        self.set_start_time(value)

    def set_start_time(self, value: float) -> "Movie":
        self._archive["startTime"] = float(value)
        self._slide._mark_dirty()
        return self

    @property
    def end_time(self) -> Optional[float]:
        v = self._archive.get("endTime")
        return float(v) if v is not None else None

    @end_time.setter
    def end_time(self, value: float):
        self.set_end_time(value)

    def set_end_time(self, value: float) -> "Movie":
        self._archive["endTime"] = float(value)
        self._slide._mark_dirty()
        return self

    def set_trim(self, start: float, end: float) -> "Movie":
        """Set both start and end time at once."""
        return self.set_start_time(start).set_end_time(end)

    @property
    def poster_time(self) -> Optional[float]:
        v = self._archive.get("posterTime")
        return float(v) if v is not None else None

    @poster_time.setter
    def poster_time(self, value: float):
        self.set_poster_time(value)

    def set_poster_time(self, value: float) -> "Movie":
        self._archive["posterTime"] = float(value)
        self._slide._mark_dirty()
        return self

    @property
    def duration(self) -> Optional[float]:
        """end_time - start_time (computed convenience)."""
        st = self.start_time
        et = self.end_time
        if st is None or et is None:
            return None
        return et - st

    # ---- volume ----

    @property
    def volume(self) -> Optional[float]:
        v = self._archive.get("volume")
        return float(v) if v is not None else None

    @volume.setter
    def volume(self, value: float):
        self.set_volume(value)

    def set_volume(self, value: float) -> "Movie":
        v = float(value)
        if v < 0.0 or v > 1.0:
            raise ValueError(f"volume must be in [0.0, 1.0], got {v}")
        self._archive["volume"] = v
        self._slide._mark_dirty()
        return self

    def mute(self) -> "Movie":
        return self.set_volume(0.0)

    def unmute(self, value: float = 1.0) -> "Movie":
        return self.set_volume(value)

    @property
    def is_muted(self) -> bool:
        return (self.volume or 0.0) == 0.0

    # ---- loop ----

    @property
    def loop(self) -> Optional[str]:
        """Raw loop option string ("None" / "Repeat" / "BackAndForth")."""
        return self._archive.get("loopOption")

    @loop.setter
    def loop(self, value: str):
        self.set_loop(value)

    def set_loop(self, value: str) -> "Movie":
        """Set loop behavior. Accepts aliases ('off'/'loop'/'pingpong')
        or the raw enum strings ('None'/'Repeat'/'BackAndForth')."""
        self._archive["loopOption"] = resolve_loop(value)
        self._slide._mark_dirty()
        return self

    @property
    def is_looping(self) -> bool:
        return self.loop in (LOOP_REPEAT, LOOP_BACK_AND_FORTH)

    # ---- multi-slide playback ----

    @property
    def plays_across_slides(self) -> bool:
        return bool(self._archive.get("playsAcrossSlides", False))

    @plays_across_slides.setter
    def plays_across_slides(self, value: bool):
        self.set_plays_across_slides(value)

    def set_plays_across_slides(self, value: bool) -> "Movie":
        self._archive["playsAcrossSlides"] = bool(value)
        self._slide._mark_dirty()
        return self

    # ---- references (read-only — these point to embedded blobs) ----

    @property
    def media_data_id(self) -> Optional[str]:
        d = self._archive.get("movieData")
        if isinstance(d, dict):
            v = d.get("identifier")
            return str(v) if v is not None else None
        return None

    @property
    def poster_image_id(self) -> Optional[str]:
        d = self._archive.get("posterImageData")
        if isinstance(d, dict):
            v = d.get("identifier")
            return str(v) if v is not None else None
        return None

    @property
    def style_id(self) -> Optional[str]:
        d = self._archive.get("style")
        if isinstance(d, dict):
            v = d.get("identifier")
            return str(v) if v is not None else None
        return None

    @property
    def streaming(self) -> bool:
        return bool(self._archive.get("streaming", False))

    @property
    def natural_size(self) -> Optional[tuple[float, float]]:
        d = self._archive.get("naturalSize")
        if isinstance(d, dict):
            w = d.get("width")
            h = d.get("height")
            if w is not None and h is not None:
                return (float(w), float(h))
        return None

    # ---- summary ----

    def summary(self) -> dict[str, Any]:
        return {
            "archive_id": self._archive_id,
            "audio_only": self.is_audio_only,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "poster_time": self.poster_time,
            "volume": self.volume,
            "loop": self.loop,
            "plays_across_slides": self.plays_across_slides,
            "streaming": self.streaming,
            "natural_size": self.natural_size,
            "media_data_id": self.media_data_id,
            "poster_image_id": self.poster_image_id,
            "style_id": self.style_id,
        }

    def __repr__(self):
        return (
            f"<Movie #{self._archive_id} loop={self.loop} "
            f"trim={self.start_time}-{self.end_time}s vol={self.volume} "
            f"audio_only={self.is_audio_only} across_slides={self.plays_across_slides}>"
        )


# ============================================================
# Soundtrack proxy (deck-level audio)
# ============================================================


class Soundtrack(RawArchiveMixin):
    """Wraps the deck-level :class:`KN.Soundtrack` (lives in
    Document.iwa). One per deck."""

    def __init__(self, *, deck, archive: dict[str, Any]):
        self._deck = deck
        self._archive = archive

    # ---- RawArchiveMixin hooks ----

    def _raw_archive_root(self) -> dict:
        return self._archive

    def _raw_mark_dirty(self) -> None:
        self._deck._mark_document_dirty()

    @property
    def mode(self) -> Optional[str]:
        return self._archive.get("mode")

    @mode.setter
    def mode(self, value: str):
        self.set_mode(value)

    def set_mode(self, value: str) -> "Soundtrack":
        """Set soundtrack mode. Accepts aliases ('once'/'loop'/'off')
        or the raw enum strings."""
        self._archive["mode"] = resolve_soundtrack_mode(value)
        self._deck._mark_document_dirty()
        return self

    @property
    def mode_name(self) -> Optional[str]:
        m = self.mode
        if isinstance(m, str) and m.startswith("kKNSoundtrackMode"):
            return m[len("kKNSoundtrackMode"):].lower()
        return None

    @property
    def volume(self) -> Optional[float]:
        v = self._archive.get("volume")
        return float(v) if v is not None else None

    @volume.setter
    def volume(self, value: float):
        self.set_volume(value)

    def set_volume(self, value: float) -> "Soundtrack":
        v = float(value)
        if v < 0.0 or v > 1.0:
            raise ValueError(f"volume must be in [0.0, 1.0], got {v}")
        self._archive["volume"] = v
        self._deck._mark_document_dirty()
        return self

    @property
    def is_loop(self) -> bool:
        return self.mode == SOUNDTRACK_LOOP

    @property
    def is_off(self) -> bool:
        return self.mode == SOUNDTRACK_OFF

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "mode_name": self.mode_name,
            "volume": self.volume,
        }

    def __repr__(self):
        return f"<Soundtrack mode={self.mode_name} volume={self.volume}>"


# ============================================================
# LiveVideoSource proxy
# ============================================================


class LiveVideoSource(RawArchiveMixin):
    """Wraps a single :class:`KN.LiveVideoSource` config entry. These
    define camera feeds that can be embedded as drawables. Lives in
    Document.iwa under KN.LiveVideoSourceCollection.

    Read-only for now (4c.5 base); future iteration may add
    add_camera/remove_camera helpers.
    """

    def __init__(self, *, deck, archive: dict[str, Any]):
        self._deck = deck
        self._archive = archive

    # ---- RawArchiveMixin hooks ----

    def _raw_archive_root(self) -> dict:
        return self._archive

    def _raw_mark_dirty(self) -> None:
        self._deck._mark_document_dirty()

    @property
    def name(self) -> Optional[str]:
        return self._archive.get("name")

    @name.setter
    def name(self, value: str):
        self.set_name(value)

    def set_name(self, value: str) -> "LiveVideoSource":
        self._archive["name"] = str(value)
        self._deck._mark_document_dirty()
        return self

    @property
    def is_default(self) -> bool:
        return bool(self._archive.get("isDefaultSource", False))

    def set_default(self, value: bool) -> "LiveVideoSource":
        self._archive["isDefaultSource"] = bool(value)
        self._deck._mark_document_dirty()
        return self

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "is_default": self.is_default,
        }

    def __repr__(self):
        return f"<LiveVideoSource name={self.name!r} default={self.is_default}>"
