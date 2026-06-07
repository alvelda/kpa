"""
kpa.animations — Build (on-slide) animations + slide transitions
================================================================

Step 4c.4 of the editable-surface expansion.

**KN.BuildArchive** is a single on-slide animation entry. It lives as
a *sibling archive* to the KN.SlideArchive (same slide YAML file, own
identifier). Each build references its target shape by
``drawable.identifier``.

Schema (observed in SVEF + NCI):

  KN.BuildArchive:
    attributes:
      animationAttributes:
        effect: str   (e.g. "apple:dissolve character", "apple:gallery-appear")
        animationType: str  ("In" / "Out" / "Action" / "Content")
        delay: float
        duration: float
        randomNumberSeed: int
        writingDirectionIsRtl: bool
      customTextDelivery: str | None  (None / kTextDeliveryByObject /
                                       kTextDeliveryByParagraph /
                                       kTextDeliveryByWord /
                                       kTextDeliveryByCharacter)
      customDeliveryOption: str | None  (None / kDeliveryOptionForward /
                                        kDeliveryOptionReverse)
      eventTrigger: int   (1 = on-click; 2 = with previous; 3 = after previous)
    delivery: str         (top-level summary, e.g. "All at Once")
    drawable:
      identifier: str     (target shape id)
    duration: float       (top-level summary duration — often 0.0)
    chunkIdSeed: int

**Slide transitions** live on ``KN.SlideArchive.transition.attributes.
animationAttributes`` with the same animationAttributes shape plus:
  - direction: int   (a transition-specific compass enum)
  - isAutomatic: bool
  - animationType: "Transition"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kpa.objects import Slide


# Event trigger constants (Keynote's enum is 1-based)
TRIGGER_ON_CLICK = 1
TRIGGER_WITH_PREVIOUS = 2
TRIGGER_AFTER_PREVIOUS = 3

# Animation type constants
ANIM_TYPE_IN = "In"
ANIM_TYPE_OUT = "Out"
ANIM_TYPE_ACTION = "Action"
ANIM_TYPE_CONTENT = "Content"
ANIM_TYPE_TRANSITION = "Transition"

# Custom text delivery enum strings
TEXT_DELIVERY_BY_OBJECT = "kTextDeliveryByObject"
TEXT_DELIVERY_BY_PARAGRAPH = "kTextDeliveryByParagraph"
TEXT_DELIVERY_BY_WORD = "kTextDeliveryByWord"
TEXT_DELIVERY_BY_CHARACTER = "kTextDeliveryByCharacter"

# Custom delivery direction enum strings
DELIVERY_OPTION_FORWARD = "kDeliveryOptionForward"
DELIVERY_OPTION_REVERSE = "kDeliveryOptionReverse"


# Common effect names (apple:* prefixed). Not exhaustive — agents can
# pass any effect string Keynote recognizes; these are convenience
# defaults for the most-used transitions/builds.
EFFECTS = {
    # appear/disappear basics
    "appear": "apple:appear",
    "disappear": "apple:disappear",
    "fade": "apple:dissolve",
    "fade_character": "apple:dissolve character",
    # motion-style entrances
    "push": "apple:push",
    "fly_in": "apple:fly-in",
    "fly_out": "apple:fly-out",
    "blast": "apple:blast",
    "drift_in": "apple:drift in",
    "scale": "apple:scale",
    "scale_big": "apple:scale-big",
    "rotate": "apple:rotate",
    "swing": "apple:swing",
    "wipe": "apple:wipe",
    "blink": "apple:blink",
    "bounce": "apple:bounce",
    "pulse": "apple:pulse",
    "shake": "apple:shake",
    "gallery": "apple:gallery-appear",
    "movie_start": "apple:movie-start",
    # slide-only transitions
    "magic_move": "apple:magic move",
    "cube": "apple:cube",
    "flip": "apple:flip",
    "swap": "apple:swap",
    "page_flip": "apple:page flip",
    "shimmer": "apple:shimmer",
    "spin": "apple:spin",
    "twirl": "apple:twirl",
    "doorway": "apple:doorway",
}


def resolve_effect(name: str) -> str:
    """Translate a short alias ("push", "fade") into the apple: form.
    Unknown names pass through unchanged (so any Keynote-recognized
    string still works)."""
    return EFFECTS.get(name.lower(), name)


# ============================================================
# Build (on-slide animation)
# ============================================================


class Build:
    """Wraps a single :class:`KN.BuildArchive`. Provides read+write
    access to effect / duration / delay / target / animation type /
    text delivery / trigger."""

    def __init__(self, *, slide: "Slide", archive: dict[str, Any], archive_id: str):
        self._slide = slide
        self._archive = archive
        self._archive_id = archive_id

    # ---- internals ----

    def _attrs(self) -> dict[str, Any]:
        a = self._archive.setdefault("attributes", {})
        if not isinstance(a, dict):
            a = {}
            self._archive["attributes"] = a
        return a

    def _anim_attrs(self) -> dict[str, Any]:
        attrs = self._attrs()
        aa = attrs.setdefault("animationAttributes", {})
        if not isinstance(aa, dict):
            aa = {}
            attrs["animationAttributes"] = aa
        return aa

    @property
    def archive_id(self) -> str:
        return self._archive_id

    # ---- target shape ----

    @property
    def target_id(self) -> Optional[str]:
        d = self._archive.get("drawable")
        if isinstance(d, dict):
            v = d.get("identifier")
            return str(v) if v is not None else None
        return None

    def set_target(self, shape_id: str | int) -> "Build":
        self._archive["drawable"] = {"identifier": str(shape_id)}
        self._slide._mark_dirty()
        return self

    # ---- effect ----

    @property
    def effect(self) -> Optional[str]:
        return self._anim_attrs().get("effect")

    @effect.setter
    def effect(self, value: str):
        self.set_effect(value)

    def set_effect(self, value: str) -> "Build":
        """Set the effect. Accepts either a Keynote effect string
        ("apple:push") or one of the short aliases in :data:`EFFECTS`
        ("push" / "fade" / "fly_in" / ...).
        """
        self._anim_attrs()["effect"] = resolve_effect(value)
        self._slide._mark_dirty()
        return self

    # ---- timing ----

    @property
    def duration(self) -> Optional[float]:
        v = self._anim_attrs().get("duration")
        return float(v) if v is not None else None

    @duration.setter
    def duration(self, value: float):
        self.set_duration(value)

    def set_duration(self, value: float) -> "Build":
        self._anim_attrs()["duration"] = float(value)
        self._slide._mark_dirty()
        return self

    @property
    def delay(self) -> Optional[float]:
        v = self._anim_attrs().get("delay")
        return float(v) if v is not None else None

    @delay.setter
    def delay(self, value: float):
        self.set_delay(value)

    def set_delay(self, value: float) -> "Build":
        self._anim_attrs()["delay"] = float(value)
        self._slide._mark_dirty()
        return self

    # ---- animation type (In/Out/Action/Content) ----

    @property
    def animation_type(self) -> Optional[str]:
        return self._anim_attrs().get("animationType")

    @animation_type.setter
    def animation_type(self, value: str):
        self.set_animation_type(value)

    def set_animation_type(self, value: str) -> "Build":
        if value not in (ANIM_TYPE_IN, ANIM_TYPE_OUT, ANIM_TYPE_ACTION, ANIM_TYPE_CONTENT):
            # be permissive — Keynote has more types than we enumerate
            pass
        self._anim_attrs()["animationType"] = value
        self._slide._mark_dirty()
        return self

    # ---- text delivery ----

    _TEXT_DELIVERY_NAMES = {
        "object": TEXT_DELIVERY_BY_OBJECT,
        "by_object": TEXT_DELIVERY_BY_OBJECT,
        "paragraph": TEXT_DELIVERY_BY_PARAGRAPH,
        "by_paragraph": TEXT_DELIVERY_BY_PARAGRAPH,
        "word": TEXT_DELIVERY_BY_WORD,
        "by_word": TEXT_DELIVERY_BY_WORD,
        "character": TEXT_DELIVERY_BY_CHARACTER,
        "by_character": TEXT_DELIVERY_BY_CHARACTER,
    }

    @property
    def text_delivery(self) -> Optional[str]:
        """The full ``kTextDeliveryBy*`` enum string, or ``None``."""
        return self._attrs().get("customTextDelivery")

    @property
    def text_delivery_name(self) -> Optional[str]:
        v = self.text_delivery
        if isinstance(v, str) and v.startswith("kTextDeliveryBy"):
            return v[len("kTextDeliveryBy"):].lower()
        return None

    def set_text_delivery(self, value: Optional[str]) -> "Build":
        """Set custom text delivery. Accepts short names
        ('object'/'paragraph'/'word'/'character') or full enum names,
        or ``None`` to clear.
        """
        if value is None:
            self._attrs()["customTextDelivery"] = None
        else:
            enum_val = self._TEXT_DELIVERY_NAMES.get(value.lower(), value)
            self._attrs()["customTextDelivery"] = enum_val
        self._slide._mark_dirty()
        return self

    @property
    def delivery_direction(self) -> Optional[str]:
        """'forward' / 'reverse' / None."""
        v = self._attrs().get("customDeliveryOption")
        if isinstance(v, str):
            if v == DELIVERY_OPTION_FORWARD:
                return "forward"
            if v == DELIVERY_OPTION_REVERSE:
                return "reverse"
        return None

    def set_delivery_direction(self, value: Optional[str]) -> "Build":
        if value is None:
            self._attrs()["customDeliveryOption"] = None
        elif value.lower() == "forward":
            self._attrs()["customDeliveryOption"] = DELIVERY_OPTION_FORWARD
        elif value.lower() == "reverse":
            self._attrs()["customDeliveryOption"] = DELIVERY_OPTION_REVERSE
        else:
            raise ValueError(f"delivery_direction must be 'forward'/'reverse'/None, got {value!r}")
        self._slide._mark_dirty()
        return self

    # ---- event trigger ----

    @property
    def trigger(self) -> Optional[int]:
        v = self._attrs().get("eventTrigger")
        return int(v) if v is not None else None

    @property
    def trigger_name(self) -> Optional[str]:
        return {
            TRIGGER_ON_CLICK: "on_click",
            TRIGGER_WITH_PREVIOUS: "with_previous",
            TRIGGER_AFTER_PREVIOUS: "after_previous",
        }.get(self.trigger)

    def set_trigger(self, value) -> "Build":
        if isinstance(value, str):
            iv = {
                "on_click": TRIGGER_ON_CLICK,
                "click": TRIGGER_ON_CLICK,
                "with_previous": TRIGGER_WITH_PREVIOUS,
                "with": TRIGGER_WITH_PREVIOUS,
                "after_previous": TRIGGER_AFTER_PREVIOUS,
                "after": TRIGGER_AFTER_PREVIOUS,
            }.get(value.lower())
            if iv is None:
                raise ValueError(
                    f"Unknown trigger {value!r}; use on_click / with_previous / after_previous"
                )
            value = iv
        self._attrs()["eventTrigger"] = int(value)
        self._slide._mark_dirty()
        return self

    # ---- summary ----

    def summary(self) -> dict[str, Any]:
        return {
            "archive_id": self._archive_id,
            "target_id": self.target_id,
            "effect": self.effect,
            "duration": self.duration,
            "delay": self.delay,
            "animation_type": self.animation_type,
            "text_delivery": self.text_delivery_name,
            "delivery_direction": self.delivery_direction,
            "trigger": self.trigger_name,
        }

    def __repr__(self):
        return (
            f"<Build #{self._archive_id} effect={self.effect!r} "
            f"type={self.animation_type} target={self.target_id} "
            f"dur={self.duration} delay={self.delay} trigger={self.trigger_name}>"
        )


# ============================================================
# Transition (between-slide)
# ============================================================


class Transition:
    """Wraps a slide's transition (``KN.SlideArchive.transition``).

    Transition fields mirror an animation's ``animationAttributes``
    block plus transition-specific extras (``direction``,
    ``isAutomatic``).
    """

    def __init__(self, *, slide: "Slide", slide_archive: dict[str, Any]):
        self._slide = slide
        self._slide_archive = slide_archive

    def _trans_root(self) -> dict[str, Any]:
        t = self._slide_archive.setdefault("transition", {})
        if not isinstance(t, dict):
            t = {}
            self._slide_archive["transition"] = t
        a = t.setdefault("attributes", {})
        if not isinstance(a, dict):
            a = {}
            t["attributes"] = a
        aa = a.setdefault("animationAttributes", {})
        if not isinstance(aa, dict):
            aa = {}
            a["animationAttributes"] = aa
        # Set animationType marker
        aa.setdefault("animationType", ANIM_TYPE_TRANSITION)
        return aa

    @property
    def effect(self) -> Optional[str]:
        return self._trans_root().get("effect")

    @effect.setter
    def effect(self, value: str):
        self.set_effect(value)

    def set_effect(self, value: str) -> "Transition":
        self._trans_root()["effect"] = resolve_effect(value)
        self._slide._mark_dirty()
        return self

    @property
    def duration(self) -> Optional[float]:
        v = self._trans_root().get("duration")
        return float(v) if v is not None else None

    @duration.setter
    def duration(self, value: float):
        self.set_duration(value)

    def set_duration(self, value: float) -> "Transition":
        self._trans_root()["duration"] = float(value)
        self._slide._mark_dirty()
        return self

    @property
    def delay(self) -> Optional[float]:
        v = self._trans_root().get("delay")
        return float(v) if v is not None else None

    @delay.setter
    def delay(self, value: float):
        self.set_delay(value)

    def set_delay(self, value: float) -> "Transition":
        self._trans_root()["delay"] = float(value)
        self._slide._mark_dirty()
        return self

    @property
    def direction(self) -> Optional[int]:
        v = self._trans_root().get("direction")
        return int(v) if v is not None else None

    def set_direction(self, value: int) -> "Transition":
        """Set transition direction (a Keynote-specific compass enum)."""
        self._trans_root()["direction"] = int(value)
        self._slide._mark_dirty()
        return self

    @property
    def is_automatic(self) -> bool:
        return bool(self._trans_root().get("isAutomatic", False))

    @is_automatic.setter
    def is_automatic(self, value: bool):
        self.set_automatic(value)

    def set_automatic(self, value: bool) -> "Transition":
        self._trans_root()["isAutomatic"] = bool(value)
        self._slide._mark_dirty()
        return self

    def summary(self) -> dict[str, Any]:
        return {
            "effect": self.effect,
            "duration": self.duration,
            "delay": self.delay,
            "direction": self.direction,
            "is_automatic": self.is_automatic,
        }

    def __repr__(self):
        return (
            f"<Transition effect={self.effect!r} dur={self.duration} "
            f"delay={self.delay} dir={self.direction} auto={self.is_automatic}>"
        )
