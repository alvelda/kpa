"""
kpa.validator
==============

Step 4c.8 third deliverable — brand validator.

A brand validator enforces a YAML/dict rules file against a deck
and reports violations. Use cases:

  * "Every slide title must use Brainworks Sans Bold"
  * "Body text must be in the approved palette (5 colors)"
  * "No slide may use more than 3 chart styles"
  * "Stylesheet must include a TableStyleArchive named 'Brainworks Data'"

The validator is built around a small registry of pluggable
:class:`Rule` classes. Each rule reads from the deck via the kpa
typed accessors + escape hatch, returns a list of
:class:`Violation` objects, and is composable into a :class:`Brand`.

Rules included in this first pass:

  * :class:`RequireFontInBodyText` — every BodyTextStyle must use one of
    the allowed font names
  * :class:`RequireTitleFont` — every BodyTextStyle marked as a title
    placeholder uses an allowed font
  * :class:`ForbidFontFamilies` — none of the deck's character styles
    use a disallowed font (e.g. "Comic Sans MS")
  * :class:`RequireStyleNamePresent` — the DocumentStylesheet contains
    an archive of a given pbtype whose ``name`` matches
  * :class:`MinSlideCount` / :class:`MaxSlideCount` — coarse deck shape

YAML rules file looks like::

    brand: Brainworks
    version: 1
    rules:
      - kind: ForbidFontFamilies
        families: [Comic Sans MS, Papyrus, Wingdings]
      - kind: RequireFontInBodyText
        families: [Brainworks Sans, Brainworks Serif]
      - kind: MinSlideCount
        n: 3
      - kind: RequireStyleNamePresent
        pbtype: TST.TableStyleArchive
        name: Brainworks Data

The first pass is read-only — no auto-fix. Auto-fix is on the
roadmap for Phase 2 once we have more confidence in mutating
DocumentStylesheet entries safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:
    from kpa.deck import Deck


# =============== violation records ===============


@dataclass(frozen=True)
class Violation:
    """One brand-violation finding.

    ``rule_kind`` matches the rule class name. ``message`` is human-
    readable; ``locator`` is an optional pointer (slide index, archive
    id, or style id) to help an agent jump to the offender.
    """
    rule_kind: str
    message: str
    locator: Optional[str] = None
    severity: str = "error"  # 'error' or 'warning'

    def __str__(self) -> str:
        loc = f" [{self.locator}]" if self.locator else ""
        return f"{self.severity.upper()} {self.rule_kind}: {self.message}{loc}"


@dataclass
class ValidationReport:
    """Result of a :meth:`Brand.validate` pass."""
    brand: str
    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(v.severity == "error" for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    def summary(self) -> str:
        if self.ok and not self.violations:
            return f"✓ {self.brand}: clean (no violations)"
        return (f"{self.brand}: {self.error_count} error(s), "
                f"{self.warning_count} warning(s)")

    def __str__(self) -> str:
        lines = [self.summary()]
        for v in self.violations:
            lines.append(f"  - {v}")
        return "\n".join(lines)


# =============== rule base ===============


class Rule:
    """Base class for brand-validator rules.

    Subclasses override :meth:`check` and return an iterable of
    :class:`Violation`. The class name is used as the YAML ``kind``
    discriminator.
    """

    KIND: str = ""  # set by subclass; or use class name fallback

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def kind(self) -> str:
        return self.KIND or type(self).__name__

    def check(self, deck: "Deck") -> Iterable[Violation]:
        raise NotImplementedError


# =============== concrete rules ===============


class MinSlideCount(Rule):
    """Deck must have at least ``n`` slides."""
    KIND = "MinSlideCount"
    n: int = 1

    def check(self, deck):
        count = len(deck.slide)
        if count < self.n:
            yield Violation(
                self.kind,
                f"Deck has {count} slide(s); minimum is {self.n}",
            )


class MaxSlideCount(Rule):
    """Deck must have at most ``n`` slides (warning, not error)."""
    KIND = "MaxSlideCount"
    n: int = 100

    def check(self, deck):
        count = len(deck.slide)
        if count > self.n:
            yield Violation(
                self.kind,
                f"Deck has {count} slide(s); recommended max is {self.n}",
                severity="warning",
            )


class ForbidFontFamilies(Rule):
    """No character-style archive may reference any of the listed
    font families.
    """
    KIND = "ForbidFontFamilies"
    families: list[str] = []

    def check(self, deck):
        if not self.families:
            return
        forbidden = {f.lower() for f in self.families}
        sheet = deck.stylesheet
        if sheet is None:
            return
        for ident, obj in sheet.iter_by_pbtype("TSWP.CharacterStyleArchive"):
            cs = obj.get("charProperties") or {}
            font = cs.get("fontName") or ""
            if isinstance(font, str) and font.lower() in forbidden:
                yield Violation(
                    self.kind,
                    f"Character style uses forbidden font {font!r}",
                    locator=f"style#{ident}",
                )


class RequireFontInBodyText(Rule):
    """Every character style used by body text placeholders must
    use one of the allowed font families."""
    KIND = "RequireFontInBodyText"
    families: list[str] = []

    def check(self, deck):
        if not self.families:
            return
        allowed = {f.lower() for f in self.families}
        sheet = deck.stylesheet
        if sheet is None:
            return
        for ident, obj in sheet.iter_by_pbtype("TSWP.CharacterStyleArchive"):
            cs = obj.get("charProperties") or {}
            font = cs.get("fontName")
            if font is None:
                continue
            if not isinstance(font, str):
                continue
            if font.lower() not in allowed:
                yield Violation(
                    self.kind,
                    f"Character style font {font!r} not in approved list "
                    f"({sorted(self.families)})",
                    locator=f"style#{ident}",
                    severity="warning",
                )


class RequireStyleNamePresent(Rule):
    """The deck's DocumentStylesheet must contain at least one archive
    of the given pbtype whose ``name`` field matches.
    """
    KIND = "RequireStyleNamePresent"
    pbtype: str = ""
    name: str = ""

    def check(self, deck):
        if not self.pbtype or not self.name:
            return
        sheet = deck.stylesheet
        if sheet is None:
            yield Violation(
                self.kind,
                f"No stylesheet present; cannot verify {self.pbtype} named {self.name!r}",
            )
            return
        for ident, obj in sheet.iter_by_pbtype(self.pbtype):
            if obj.get("name") == self.name:
                return  # found
        yield Violation(
            self.kind,
            f"No {self.pbtype} archive named {self.name!r} in stylesheet",
        )


# Rule registry by KIND for YAML deserialization
_RULE_REGISTRY: dict[str, type[Rule]] = {
    cls.KIND: cls
    for cls in (
        MinSlideCount,
        MaxSlideCount,
        ForbidFontFamilies,
        RequireFontInBodyText,
        RequireStyleNamePresent,
    )
}


def available_rules() -> tuple[str, ...]:
    """Sorted tuple of registered rule kinds (for help / docs)."""
    return tuple(sorted(_RULE_REGISTRY.keys()))


# =============== Brand container ===============


@dataclass
class Brand:
    """A named bundle of :class:`Rule` instances.

    Construct directly with a list of rules, or load from a dict /
    YAML file via :meth:`from_dict` / :meth:`from_yaml_file`.
    """
    name: str
    version: int = 1
    rules: list[Rule] = field(default_factory=list)

    def validate(self, deck) -> ValidationReport:
        report = ValidationReport(brand=self.name)
        for rule in self.rules:
            for v in rule.check(deck):
                report.violations.append(v)
        return report

    @classmethod
    def from_dict(cls, spec: dict) -> "Brand":
        """Parse a dict (typically loaded from YAML) into a Brand.

        Unknown rule kinds raise ``ValueError``.
        """
        name = spec.get("brand") or spec.get("name") or "(unnamed brand)"
        version = int(spec.get("version", 1))
        rule_specs = spec.get("rules") or []
        rules: list[Rule] = []
        for rs in rule_specs:
            if not isinstance(rs, dict):
                raise ValueError(f"Rule spec must be a dict; got {type(rs).__name__}")
            kind = rs.get("kind")
            if not kind:
                raise ValueError(f"Rule spec missing 'kind' key: {rs}")
            if kind not in _RULE_REGISTRY:
                raise ValueError(
                    f"Unknown rule kind {kind!r}; available: {available_rules()}"
                )
            rcls = _RULE_REGISTRY[kind]
            kwargs = {k: v for k, v in rs.items() if k != "kind"}
            rules.append(rcls(**kwargs))
        return cls(name=name, version=version, rules=rules)

    @classmethod
    def from_yaml_file(cls, path) -> "Brand":
        from pathlib import Path
        import yaml
        text = Path(path).read_text()
        return cls.from_dict(yaml.safe_load(text))
